package ifconfig

import (
	"satellite/data"
	"satellite/model"
	"satellite/pkg/frr"
	"sort"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/vishvananda/netlink"
)

const checkGap = 500 * time.Millisecond

var configuredLinks = make(map[string]string) // ifName -> V4Addr
var hasGSL = false
var lastMetricOrder []string
var lastOspfLinks []*model.LinkInfo

func InitInterfaceWatcher() {
	go InterfaceWatcher()
}

func InterfaceWatcher() {
	for {
		links, err := netlink.LinkList()
		if err != nil {
			logrus.Errorf("Get Link List Error: %s", err.Error())
			time.Sleep(checkGap)
			continue
		}

		topoLinks := data.TopoInfo.LinkInfos
		topoEnds := data.TopoInfo.EndInfos

		kernelLinks := make(map[string]netlink.Link)
		for _, l := range links {
			kernelLinks[l.Attrs().Name] = l
		}

		// --- Tear down links removed from topo ---
		for name := range configuredLinks {
			if _, inTopo := topoLinks[name]; !inTopo {
				if err := DelInterfaceIPs(name); err != nil {
					logrus.Errorf("Del IPs on %s Error: %s", name, err.Error())
					continue
				}
				delete(configuredLinks, name)
				logrus.Infof("Deconfigured removed interface %s", name)
			}
		}

		// --- Configure links present in topo ---
		type gslCandidate struct {
			name  string
			delay float64
			nh    GSLNexthop
		}
		var candidates []gslCandidate
		var ospfLinks []*model.LinkInfo

		for name, topoInfo := range topoLinks {
			if topoInfo == nil {
				continue
			}
			link, exists := kernelLinks[name]
			if !exists {
				continue
			}

			// Reconfigure IP if new or changed
			if configuredLinks[name] != topoInfo.V4Addr {
				if configuredLinks[name] != "" {
					DelInterfaceIPs(name)
				}
				if err := SetInterfaceIP(name, topoInfo.V4Addr); err != nil {
					logrus.Errorf("Set IP on %s Error: %s", name, err.Error())
					continue
				}
				configuredLinks[name] = topoInfo.V4Addr
				logrus.Infof("Configured %s with %s", name, topoInfo.V4Addr)
			}

			endInfo := topoEnds[name]
			if endInfo == nil {
				continue
			}

			switch endInfo.Type {
			case "GroundStation":
				gw, err := PeerGatewayIP(topoInfo.V4Addr)
				if err != nil {
					logrus.Errorf("Derive peer GW for %s Error: %s", name, err.Error())
					continue
				}
				candidates = append(candidates, gslCandidate{
					name:  name,
					delay: topoInfo.DelayMs,
					nh: GSLNexthop{
						LinkIndex: link.Attrs().Index,
						Gw:        gw,
					},
				})
			case "Satellite":
				ospfLinks = append(ospfLinks, topoInfo)
			case "GroundTerminal":
				// IP is assigned, connected route redistributed via OSPF automatically
				// Does not contribute to default route or hasGSL
			default:
				logrus.Warnf("Unknown peer type %s on interface %s", endInfo.Type, name)
			}
		}

		// --- Sort GSLs by delay, assign metrics ---
		sort.Slice(candidates, func(i, j int) bool {
			return candidates[i].delay < candidates[j].delay
		})

		newOrder := make([]string, len(candidates))
		for i, c := range candidates {
			newOrder[i] = c.name
		}

		var nexthops []GSLNexthop
		for i, c := range candidates {
			c.nh.Metric = (i + 1) * 100
			nexthops = append(nexthops, c.nh)
		}

		if !stringSliceEqual(newOrder, lastMetricOrder) {
			if err := SyncDefaultRoutes(nexthops); err != nil {
				logrus.Errorf("Sync default routes Error: %s", err.Error())
			} else {
				lastMetricOrder = newOrder
				for i, c := range candidates {
					logrus.Infof("GSL %s delay=%.2fms metric=%d", c.name, c.delay, (i+1)*100)
				}
			}
		}

		// --- Push OSPF config only when GSL presence or ISL membership changes ---
		nowHasGSL := len(candidates) > 0
		gslChanged := nowHasGSL != hasGSL
		ospfChanged := !linkSliceEqual(ospfLinks, lastOspfLinks)

		if gslChanged || ospfChanged {
			hasGSL = nowHasGSL
			lastOspfLinks = ospfLinks
			if err := frr.InitConfigBatch(ospfLinks, hasGSL); err != nil {
				logrus.Errorf("FRR InitConfigBatch Error: %s", err.Error())
			}
			if gslChanged {
				logrus.Infof("GSL presence changed: hasGSL=%v", hasGSL)
			}
		}

		time.Sleep(checkGap)
	}
}

func stringSliceEqual(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func linkSliceEqual(a, b []*model.LinkInfo) bool {
	if len(a) != len(b) {
		return false
	}
	aMap := make(map[string]bool)
	for _, l := range a {
		aMap[l.V4Addr] = true
	}
	for _, l := range b {
		if !aMap[l.V4Addr] {
			return false
		}
	}
	return true
}