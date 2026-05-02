// route_daemon.go
//
// Runs inside every container. On each topology tick:
//   - Runs ONE Dijkstra from self
//   - Installs one route per UT:  <ut_ip>/32 via <next-hop>
//   - Installs default route:     0.0.0.0/0 via <next-hop toward anchor>
//
// Hysteresis: next-hop only changes if new path is >5% cheaper AND
// the old next-hop IP still exists in the topology (i.e. link not gone).
// Topology changes (link removal) always converge immediately.
//
// Build:
//   go mod init route_daemon
//   go get github.com/vishvananda/netlink
//   go build -o route_daemon route_daemon.go
//
// Env:
//   INSTANCE_ID   required
//   TOPO_FILE     default /routes/topology.json

package route

import (
	"container/heap"
	"encoding/json"
	"user/config"
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
	IP   string `json:"ip"` // set for UT nodes — route destination
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

// ---- Dijkstra -----------------------------------------------------------

type Edge struct {
	to     string
	via    string // next-hop IP to reach this neighbor
	weight int
}

type Item struct {
	node     string
	dist     int
	firstHop string
	index    int
}

type PQ []*Item

func (pq PQ) Len() int            { return len(pq) }
func (pq PQ) Less(i, j int) bool  { return pq[i].dist < pq[j].dist }
func (pq PQ) Swap(i, j int)       { pq[i], pq[j] = pq[j], pq[i]; pq[i].index = i; pq[j].index = j }
func (pq *PQ) Push(x interface{}) { item := x.(*Item); item.index = len(*pq); *pq = append(*pq, item) }
func (pq *PQ) Pop() interface{}   { old := *pq; n := len(old); item := old[n-1]; *pq = old[0 : n-1]; return item }

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
			if nd < results[e.to].dist {
				fh := cur.firstHop
				if cur.node == src {
					fh = e.via
				}
				results[e.to] = Result{dist: nd, firstHop: fh}
				heap.Push(pq, &Item{node: e.to, dist: nd, firstHop: fh})
			}
		}
	}
	return results
}

func buildGraph(topo *Topology) map[string][]Edge {
	// Seed all nodes — even isolated ones appear in results
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

// buildReachableIPs returns the set of all next-hop IPs currently active
// in the topology. Used for hysteresis: if old next-hop is not in this set,
// its link is gone and we must reroute immediately.
func buildReachableIPs(topo *Topology) map[string]bool {
	ips := make(map[string]bool, len(topo.Links)*2)
	for _, link := range topo.Links {
		ips[link.AIP] = true
		ips[link.BIP] = true
	}
	return ips
}

func findAnchorID(topo *Topology) string {
	// Deterministic: pick lowest lexicographic ID among anchor nodes
	best := ""
	for id, n := range topo.Nodes {
		if n.Type == "anchor" && (best == "" || id < best) {
			best = id
		}
	}
	return best
}

// ---- Hysteresis state ---------------------------------------------------

const rerouteThreshold = 0.05 // only reroute if >5% improvement

type installedEntry struct {
	via  string
	cost int
}

var installed = map[string]installedEntry{} // dst -> {via, cost}

// shouldUpdate decides whether to switch to a new next-hop.
// Returns (hop to use, whether a netlink update is needed).
func shouldUpdate(dst, newHop string, newCost int, reachableIPs map[string]bool) (string, bool) {
	cur, exists := installed[dst]
	if !exists {
		// First time — always install
		return newHop, true
	}
	if cur.via == newHop {
		// Same hop — no change
		return newHop, false
	}
	// Different hop — check if old one is still alive
	if !reachableIPs[cur.via] {
		// Old next-hop link is gone — reroute immediately, no hysteresis
		return newHop, true
	}
	// Old hop still alive — only switch if meaningfully better
	if cur.cost > 0 {
		improvement := float64(cur.cost-newCost) / float64(cur.cost)
		if improvement < rerouteThreshold {
			return cur.via, false // suppress churn
		}
	}
	return newHop, true
}

// ---- Netlink route management -------------------------------------------

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

// resolveLink finds the interface index for a given gateway IP.
// Without this, kernel may pick a linkdown interface when multiple
// interfaces share the same subnet (stale handover interfaces).
func resolveLink(gw net.IP) int {
	routes, err := netlink.RouteGet(gw)
	if err != nil || len(routes) == 0 {
		return 0
	}
	return routes[0].LinkIndex
}

// netlinkReplace uses RTM_NEWROUTE+NLM_F_REPLACE — atomic, no gap.
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

func applyRoutes(desired []RouteEntry, reachableIPs map[string]bool) {
	desiredDsts := make(map[string]bool, len(desired))

	for _, r := range desired {
		desiredDsts[r.dst] = true
		hop, needUpdate := shouldUpdate(r.dst, r.via, r.cost, reachableIPs)
		if !needUpdate {
			continue
		}
		if err := netlinkReplace(r.dst, hop); err != nil {
			log.Printf("[route] replace %s via %s failed: %v", r.dst, hop, err)
			continue
		}
		log.Printf("[route] replace %s via %s (cost=%d)", r.dst, hop, r.cost)
		installed[r.dst] = installedEntry{via: hop, cost: r.cost}
	}

	// Remove stale routes
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

	// Operator restart detection
	if topo.Tick == 1 && lastTick > 1 {
		log.Printf("operator restarted, clearing installed routes")
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
	reachableIPs := buildReachableIPs(&topo)
	results := dijkstra(graph, selfID)

	anchorID := findAnchorID(&topo)
	var desired []RouteEntry

	for nodeID, info := range topo.Nodes {
		r, ok := results[nodeID]
		if !ok || r.firstHop == "" || r.dist == math.MaxInt64 {
			continue
		}

		switch info.Type {
		case "ut":
			// Route to this UT's fixed IP
			utIP := info.IP
			if utIP == "" {
				continue
			}
			if !strings.Contains(utIP, "/") {
				utIP += "/32"
			}
			desired = append(desired, RouteEntry{dst: utIP, via: r.firstHop, cost: r.dist})

		case "anchor":
			// Only install default via the deterministic anchor
			if nodeID == anchorID && nodeID != selfID {
				desired = append(desired, RouteEntry{dst: "0.0.0.0/0", via: r.firstHop, cost: r.dist})
			}
		}
	}

	applyRoutes(desired, reachableIPs)
	log.Printf("[tick %d] done in %v", topo.Tick, time.Since(start))
	return true
}

// ---- Main ---------------------------------------------------------------

func InitDijkstra() {
	selfID = config.HostName
	if selfID == "" {
		log.Fatal("INSTANCE_ID env var required")
	}
	// topoFile = os.Getenv("TOPO_FILE")
	// if topoFile == "" {
	topoFile = "/share/topo/topology.json"
	// }
	log.Printf("route_daemon starting: self=%s topo=%s", selfID, topoFile)
	if _, err := os.Stat(topoFile); err == nil {
		processTopology(topoFile)
	}
	watchFile(topoFile)
}
