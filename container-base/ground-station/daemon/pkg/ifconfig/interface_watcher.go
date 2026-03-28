package ifconfig

import (
	"ground/data"
	"ground/model"
	"ground/pkg/frr"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/vishvananda/netlink"
)

const checkGap = 500 * time.Millisecond

var linkReadymap = make(map[string]bool)

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
		for _, link := range links {
			if linkReadymap[link.Attrs().Name] {
				continue
			}
			topoInfo, ok := data.TopoInfo.LinkInfos[link.Attrs().Name]
			if !ok || topoInfo == nil {
				linkReadymap[link.Attrs().Name] = false
				continue
			}

			// Step 1: assign the IP. This is idempotent — AddrAdd returns
			// EEXIST if the address is already set, which we can safely ignore.
			if err := SetInterfaceIP(link.Attrs().Name, topoInfo.V4Addr); err != nil {
				logrus.Errorf("Set Addr %s to %s Error: %s",
					topoInfo.V4Addr, link.Attrs().Name, err.Error())
				// Do NOT mark ready — retry next tick.
				continue
			}

			// Step 2: push OSPF config. This blocks until ospfd is healthy
			// (via WaitForOspfd inside WriteOspfConfig). If ospfd is still
			// restarting this will wait, not silently fail.
			if err := frr.InitConfigBatch([]*model.LinkInfo{topoInfo}); err != nil {
				logrus.Errorf("Init OSPF config for interface %s Error: %s — will retry",
					link.Attrs().Name, err.Error())
				// Do NOT mark ready — retry next tick so OSPF is eventually
				// configured once ospfd recovers.
				continue
			}

			logrus.Infof("Init Interface %s Success.", link.Attrs().Name)
			linkReadymap[link.Attrs().Name] = true
		}
		time.Sleep(checkGap)
	}
}