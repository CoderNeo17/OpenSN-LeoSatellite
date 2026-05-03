package route
// route_daemon.go
//
// Build:
//   go mod init route_daemon
//   go get github.com/vishvananda/netlink
//   go build -o route_daemon route_daemon.go
//
// Env:
//   INSTANCE_ID   required
//   TOPO_FILE     default /routes/topology.json

import (
	"container/heap"
	"encoding/json"
	"log"
	"math"
	"net"
	"os"
	"strings"
	"syscall"
	"time"
	"unsafe"

	"github.com/vishvananda/netlink"
)

// ---- Topology -----------------------------------------------------------

type NodeInfo struct {
	Type string `json:"type"`
}

type LinkInfo struct {
	A      string `json:"a"`
	B      string `json:"b"`
	AIP    string `json:"a_ip"`
	BIP    string `json:"b_ip"`
	Weight int    `json:"weight"`
}

type Topology struct {
	Tick  int                 `json:"tick"`
	Nodes map[string]NodeInfo `json:"nodes"`
	Links []LinkInfo          `json:"links"`
}

// ---- Topology helpers ---------------------------------------------------

// findNodeIP returns the IP of nodeID by scanning link entries.
// For any node, its reachable IP is on one side of one of its links.
// Returns the first IP found — for UT/anchor which have one link, this
// is deterministic.
func findNodeIP(topo *Topology, nodeID string) string {
	for _, link := range topo.Links {
		if link.A == nodeID {
			return link.AIP
		}
		if link.B == nodeID {
			return link.BIP
		}
	}
	return ""
}

// findAnchorID returns the lexicographically smallest anchor node ID.
// Deterministic across all containers regardless of Go map iteration order.
func findAnchorID(topo *Topology) string {
	best := ""
	for id, n := range topo.Nodes {
		if n.Type == "Anchor" && (best == "" || id < best) {
			best = id
		}
	}
	return best
}

// ---- Dijkstra -----------------------------------------------------------

type Edge struct {
	to     string
	via    string
	weight int
}

type Item struct {
	node     string
	dist     int
	firstHop string
	index    int
}

type PQ []*Item

func (pq PQ) Len() int { return len(pq) }

// Less sorts by dist first; ties broken by firstHop lexicographically.
// This guarantees Dijkstra produces an identical result every tick as long
// as the topology is unchanged — which means the installed hop will always
// equal the computed hop on a stable topology, and applyRoutes becomes a
// no-op. No hysteresis machinery needed.
func (pq PQ) Less(i, j int) bool {
	if pq[i].dist != pq[j].dist {
		return pq[i].dist < pq[j].dist
	}
	return pq[i].firstHop < pq[j].firstHop
}

func (pq PQ) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
	pq[i].index = i
	pq[j].index = j
}
func (pq *PQ) Push(x interface{}) {
	item := x.(*Item)
	item.index = len(*pq)
	*pq = append(*pq, item)
}
func (pq *PQ) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	*pq = old[0 : n-1]
	return item
}

type Result struct {
	dist     int
	firstHop string
}

func dijkstra(graph map[string][]Edge, src string) map[string]Result {
	results := make(map[string]Result, len(graph))
	for n := range graph {
		results[n] = Result{dist: math.MaxInt64}
	}
	results[src] = Result{dist: 0}
	pq := &PQ{}
	heap.Push(pq, &Item{node: src, dist: 0})
	for pq.Len() > 0 {
		cur := heap.Pop(pq).(*Item)
		if cur.dist > results[cur.node].dist {
			continue
		}
		for _, e := range graph[cur.node] {
			nd := cur.dist + e.weight
			fh := cur.firstHop
			if cur.node == src {
				fh = e.via
			}
			prev := results[e.to]
			// Update if strictly shorter, or equal cost with lex-smaller
			// first-hop. Must mirror the PQ Less logic exactly so the
			// results map always agrees with what the PQ converged to.
			if nd < prev.dist || (nd == prev.dist && fh < prev.firstHop) {
				results[e.to] = Result{dist: nd, firstHop: fh}
				heap.Push(pq, &Item{node: e.to, dist: nd, firstHop: fh})
			}
		}
	}
	return results
}

func buildGraph(topo *Topology) map[string][]Edge {
	graph := make(map[string][]Edge, len(topo.Nodes))
	for id := range topo.Nodes {
		graph[id] = nil
	}
	for _, link := range topo.Links {
		graph[link.A] = append(graph[link.A], Edge{to: link.B, via: link.BIP, weight: link.Weight})
		graph[link.B] = append(graph[link.B], Edge{to: link.A, via: link.AIP, weight: link.Weight})
	}
	return graph
}

// ---- Route state --------------------------------------------------------

// installedEntry tracks what is currently in the kernel, used purely as a
// diff cache to avoid redundant RouteReplace syscalls — not as a hysteresis
// gate. Dijkstra's deterministic output is the sole source of truth.
type installedEntry struct {
	via  string
	cost int
}

var installed = map[string]installedEntry{}

// ---- Netlink ------------------------------------------------------------

func parseIPNet(cidr string) *net.IPNet {
	if !strings.Contains(cidr, "/") {
		cidr += "/32"
	}
	_, ipNet, err := net.ParseCIDR(cidr)
	if err != nil {
		log.Printf("parseIPNet %q: %v", cidr, err)
		return nil
	}
	return ipNet
}

// resolveLink finds the interface index to reach gw, preferring a live
// (FlagUp) interface. With multiple interfaces on the same subnet (e.g.
// orphaned veths from previous runs on the host-namespace anchor), the
// kernel's RouteGet may return a linkdown interface. We walk all routes as
// a fallback to find a live one.
func resolveLink(gw net.IP) int {
	// Fast path: RouteGet usually returns the right answer.
	routes, err := netlink.RouteGet(gw)
	if err == nil && len(routes) > 0 {
		link, lerr := netlink.LinkByIndex(routes[0].LinkIndex)
		if lerr == nil && link.Attrs().Flags&net.FlagUp != 0 {
			return routes[0].LinkIndex
		}
	}

	// Slow path: walk all routes and pick the first live interface whose
	// subnet contains gw. Handles the orphaned-veth case where multiple
	// interfaces share the same /30 but only one is up.
	allRoutes, err := netlink.RouteList(nil, netlink.FAMILY_V4)
	if err != nil {
		return 0
	}
	gwIP := gw.To4()
	for _, r := range allRoutes {
		if r.Dst == nil || r.LinkIndex == 0 {
			continue
		}
		if r.Dst.Contains(gwIP) {
			link, lerr := netlink.LinkByIndex(r.LinkIndex)
			if lerr != nil {
				continue
			}
			if link.Attrs().Flags&net.FlagUp != 0 {
				return r.LinkIndex
			}
		}
	}
	return 0
}

func netlinkReplace(dst, gwStr string) error {
	ipNet := parseIPNet(dst)
	if ipNet == nil {
		return nil
	}
	gw := net.ParseIP(gwStr)
	if gw == nil {
		log.Printf("netlinkReplace: invalid gw %q", gwStr)
		return nil
	}
	route := &netlink.Route{Dst: ipNet, Gw: gw}
	if li := resolveLink(gw); li > 0 {
		route.LinkIndex = li
	}
	return netlink.RouteReplace(route)
}

func netlinkDel(dst string) {
	ipNet := parseIPNet(dst)
	if ipNet == nil {
		return
	}
	existing, err := netlink.RouteListFiltered(netlink.FAMILY_V4,
		&netlink.Route{Dst: ipNet}, netlink.RT_FILTER_DST)
	if err != nil {
		return
	}
	for _, r := range existing {
		netlink.RouteDel(&r)
	}
}

type RouteEntry struct {
	dst  string
	via  string
	cost int
}

// applyRoutes installs desired routes into the kernel. The installed map is
// a diff cache only — if Dijkstra's output matches what's already installed,
// we skip the syscall. There is no hysteresis gating: Dijkstra's
// deterministic tie-breaking means its output is stable across ticks on an
// unchanged topology, so churn cannot occur.
func applyRoutes(desired []RouteEntry) {
	desiredDsts := make(map[string]bool, len(desired))
	for _, r := range desired {
		desiredDsts[r.dst] = true
		cur, exists := installed[r.dst]
		if exists && cur.via == r.via {
			continue // already correct, skip kernel call
		}
		if err := netlinkReplace(r.dst, r.via); err != nil {
			log.Printf("[route] replace %s via %s failed: %v", r.dst, r.via, err)
			continue
		}
		log.Printf("[route] replace %s via %s (cost=%d)", r.dst, r.via, r.cost)
		installed[r.dst] = installedEntry{via: r.via, cost: r.cost}
	}
	for dst := range installed {
		if !desiredDsts[dst] {
			netlinkDel(dst)
			log.Printf("[route] del %s (stale)", dst)
			delete(installed, dst)
		}
	}
}

// ---- inotify ------------------------------------------------------------

const (
	inCloseWrite = 0x00000008
	inMovedTo    = 0x00000080
)

func watchFile(path string) {
	for {
		fd, err := syscall.InotifyInit1(syscall.IN_CLOEXEC)
		if err != nil {
			log.Fatalf("inotify init: %v", err)
		}
		dir := path[:strings.LastIndex(path, "/")]
		if dir == "" {
			dir = "."
		}
		filename := path[strings.LastIndex(path, "/")+1:]
		syscall.InotifyAddWatch(fd, dir, inCloseWrite|inMovedTo)
		buf := make([]byte, 4096)
		for {
			n, err := syscall.Read(fd, buf)
			if err != nil {
				log.Printf("inotify read: %v", err)
				time.Sleep(10 * time.Millisecond)
				break
			}
			if n < int(unsafe.Sizeof(syscall.InotifyEvent{})) {
				continue
			}
			offset, triggered := 0, false
			for offset+16 <= n {
				nameLen := *(*uint32)(unsafe.Pointer(&buf[offset+12]))
				if offset+16+int(nameLen) > n {
					break
				}
				if nameLen > 0 {
					name := strings.TrimRight(
						string(buf[offset+16:offset+16+int(nameLen)]), "\x00")
					if name == filename {
						triggered = true
					}
				}
				offset += 16 + int(nameLen)
			}
			if triggered {
				for attempt := 0; attempt < 3; attempt++ {
					if processTopology(path) {
						break
					}
					time.Sleep(2 * time.Millisecond)
				}
			}
		}
		syscall.Close(fd)
		time.Sleep(10 * time.Millisecond)
	}
}

// ---- Core ---------------------------------------------------------------

var (
	selfID   string
	topoFile string
	lastTick = -1
)

func processTopology(path string) bool {
	data, err := os.ReadFile(path)
	if err != nil {
		log.Printf("read topo: %v", err)
		return false
	}
	var topo Topology
	if err := json.Unmarshal(data, &topo); err != nil {
		log.Printf("parse topo (will retry): %v", err)
		return false
	}

	if topo.Tick == 1 && lastTick > 1 {
		log.Printf("operator restarted, clearing state")
		installed = map[string]installedEntry{}
	}
	if topo.Tick == lastTick {
		return true
	}
	lastTick = topo.Tick

	if _, ok := topo.Nodes[selfID]; !ok {
		log.Printf("[tick %d] self %q not in topology yet", topo.Tick, selfID)
		return true
	}

	start := time.Now()
	graph := buildGraph(&topo)
	results := dijkstra(graph, selfID)
	anchorID := findAnchorID(&topo)

	var desired []RouteEntry

	for nodeID, info := range topo.Nodes {
		r, ok := results[nodeID]
		if !ok || r.firstHop == "" || r.dist == math.MaxInt64 {
			continue
		}

		switch info.Type {
		case "GroundTerminal":
			utIP := findNodeIP(&topo, nodeID)
			if utIP == "" {
				log.Printf("[tick %d] UT %s has no link IP", topo.Tick, nodeID)
				continue
			}
			desired = append(desired, RouteEntry{dst: utIP + "/32", via: r.firstHop, cost: r.dist})

		case "Anchor":
			if nodeID == anchorID && nodeID != selfID {
				desired = append(desired, RouteEntry{dst: "0.0.0.0/0", via: r.firstHop, cost: r.dist})
			}
		}
	}

	log.Printf("[tick %d] desired=%d", topo.Tick, len(desired))
	applyRoutes(desired)
	log.Printf("[tick %d] done in %v", topo.Tick, time.Since(start))
	return true
}

// ---- Main ---------------------------------------------------------------

func InitDijkstra() {
	selfIDenv,err := os.Hostname()
	if err != nil {
		log.Fatalf("get hostname: %v", err)
	}
	selfID = selfIDenv
	// topoFile = os.Getenv("/topo/topology.json")
	// if topoFile == "" {
	topoFile = "/topo/topology.json"
	// }
	log.Printf("route_daemon starting: self=%s topo=%s", selfID, topoFile)
	if _, err := os.Stat(topoFile); err == nil {
		processTopology(topoFile)
	}
	watchFile(topoFile)
}
