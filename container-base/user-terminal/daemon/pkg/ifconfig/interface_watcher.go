package ifconfig

import (
	"user/data"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/vishvananda/netlink"
)

const checkGap = 500 * time.Millisecond

var configuredLinks = make(map[string]string)

func InitInterfaceWatcher() {
	if err := EnableIPForwarding(); err != nil {
		logrus.Errorf("Enable IP Forwarding Error: %s", err.Error())
	}
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

		// Tear down removed links
		for name := range configuredLinks {
			if _, inTopo := topoLinks[name]; !inTopo {
				if err := DelInterfaceIPs(name); err != nil {
					logrus.Errorf("Del IPs on %s Error: %s", name, err.Error())
					continue
				}
				delete(configuredLinks, name)
				logrus.Infof("Deconfigured interface %s", name)
			}
		}

		// Configure present links
		for name, topoInfo := range topoLinks {
			if topoInfo == nil {
				continue
			}
			link, exists := kernelLinks[name]
			if !exists {
				continue
			}
			if configuredLinks[name] == topoInfo.V4Addr {
				continue
			}
			if configuredLinks[name] != "" {
				DelInterfaceIPs(name)
			}
			if err := SetInterfaceIP(name, topoInfo.V4Addr); err != nil {
				logrus.Errorf("Set IP on %s Error: %s", name, err.Error())
				continue
			}
			if err := ReplaceDefaultRoute(link.Attrs().Index, topoInfo.V4Addr); err != nil {
				logrus.Errorf("Set default route via %s Error: %s", name, err.Error())
				continue
			}
			configuredLinks[name] = topoInfo.V4Addr
			logrus.Infof("Configured %s with %s", name, topoInfo.V4Addr)
			_ = topoEnds[name]
		}

		time.Sleep(checkGap)
	}
}