package ifconfig

import (
	"fmt"
	"net"
	"os"
	"os/exec"
	"satellite/utils"
	"strconv"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/vishvananda/netlink"
)

func ReplaceDefaultRoute(v4Addr string) error {
	return netlink.RouteReplace(
		&netlink.Route{
			Dst: &net.IPNet{
				IP:   []byte{0, 0, 0, 0},
				Mask: []byte{0, 0, 0, 0},
			},
			Gw: net.ParseIP(v4Addr),
		},
	)
}

// func DelInterfaceIPs(ifName string) error {
// 	link, err := netlink.LinkByName(ifName)
// 	if err != nil {
// 		logrus.Errorf("Find Link By Name %s Error: %s", ifName, err.Error())
// 		return err
// 	}
// 	addrList, err := netlink.AddrList(link, netlink.FAMILY_V4)
// 	if err != nil {
// 		logrus.Errorf("Find Addr List By Link Name %s Error: %s", ifName, err.Error())
// 		return err
// 	}
// 	for _, addr := range addrList {
// 		netlink.AddrDel(link, &addr)
// 	}
// 	return nil
// }

func DelInterfaceIPs(ifName string) error {
    link, err := netlink.LinkByName(ifName)
    if err != nil {
        if _, ok := err.(netlink.LinkNotFoundError); ok {
            return nil
        }
        logrus.Errorf("Find Link By Name %s Error: %s", ifName, err.Error())
        return err
    }
    addrList, err := netlink.AddrList(link, netlink.FAMILY_V4)
	if err != nil {
		logrus.Errorf("Find Addr List By Link Name %s Error: %s", ifName, err.Error())
		return err
	}
	for _, addr := range addrList {
		netlink.AddrDel(link, &addr)
	}
	return nil
}

func SetInterfaceIP(ifName string, v4Addr string) error {
	addr := strings.Split(v4Addr, "/")
	if len(addr) < 2 {
		err := fmt.Errorf("invalid ipv4 addr %s", v4Addr)
		logrus.Errorf("Set Link %s IPv4 Addr error: %s", ifName, err.Error())
		return err
	}
	ip := net.ParseIP(addr[0])
	prefixLen, err := strconv.Atoi(addr[1])
	if err != nil {
		err = fmt.Errorf("invalid ipv4 addr prefix length %s", err.Error())
		logrus.Errorf("Set Link %s IPv4 Addr error: %s", ifName, err.Error())
		return err
	}
	link, err := netlink.LinkByName(ifName)
	if err != nil {
		logrus.Errorf("Find Link By Name %s Error: %s. Retry...", ifName, err.Error())
		return err
	}
	err = netlink.LinkSetUp(link)
	if err != nil {
		return err
	}
	netlinkAddr := netlink.Addr{
		IPNet: &net.IPNet{
			IP:   ip,
			Mask: utils.CreateV4InetMask(prefixLen),
		},
	}
	err = netlink.AddrAdd(link, &netlinkAddr)
	if err != nil {
		logrus.Errorf("Set Link %s IPv4 Addr error: %s", ifName, err.Error())
		time.Sleep(time.Second)
	}
	return nil
}

type GSLNexthop struct {
	LinkIndex int
	Gw        net.IP
	Metric    int
}

func SyncDefaultRoutes(nexthops []GSLNexthop) error {
	defaultDst := &net.IPNet{
		IP:   net.IPv4(0, 0, 0, 0),
		Mask: net.CIDRMask(0, 32),
	}
	for {
		err := netlink.RouteDel(&netlink.Route{Dst: defaultDst})
		if err != nil {
			break
		}
	}
	for _, nh := range nexthops {
		err := netlink.RouteAdd(&netlink.Route{
			Dst:       defaultDst,
			Gw:        nh.Gw,
			LinkIndex: nh.LinkIndex,
			Priority:  nh.Metric,
		})
		if err != nil {
			logrus.Errorf("Add default route via %s metric %d Error: %s", nh.Gw, nh.Metric, err.Error())
		}
	}
	return nil
}

func PeerGatewayIP(v4Addr string) (net.IP, error) {
	parts := strings.Split(v4Addr, "/")
	if len(parts) < 2 {
		return nil, fmt.Errorf("invalid addr %s", v4Addr)
	}
	ip := net.ParseIP(parts[0]).To4()
	if ip == nil {
		return nil, fmt.Errorf("invalid IPv4 %s", parts[0])
	}
	peer := make(net.IP, 4)
	copy(peer, ip)
	switch ip[3] % 4 {
	case 1:
		peer[3]++
	case 2:
		peer[3]--
	default:
		return nil, fmt.Errorf("unexpected host bits in %s", v4Addr)
	}
	return peer, nil
}

func EnableIPForwarding() error {
    return os.WriteFile("/proc/sys/net/ipv4/ip_forward", []byte("1"), 0644)
}


func EnableNAT() error {
    cmd := exec.Command(
        "iptables", "-t", "nat",
        "-A", "POSTROUTING",
        "-s", "10.0.0.0/16",
        "!", "-o", "lo",
        "-j", "MASQUERADE",
    )
    return cmd.Run()
}

func DelDefaultRoute() {
	_ = netlink.RouteDel(&netlink.Route{
		Dst: &net.IPNet{
			IP:   []byte{0, 0, 0, 0},
			Mask: []byte{0, 0, 0, 0},
		},
	})
}

func SetDefaultRouteViaEth0() error {
    link, err := netlink.LinkByName("eth0")
    if err != nil {
        logrus.Errorf("Find eth0 Error: %s", err.Error())
        return err
    }
    addrs, err := netlink.AddrList(link, netlink.FAMILY_V4)
    if err != nil || len(addrs) == 0 {
        logrus.Errorf("Get eth0 Addr Error: %s", err.Error())
        return err
    }
    // derive gateway — docker bridge gateway is always x.x.x.1
    gw := addrs[0].IP.Mask(addrs[0].Mask)
    gw[3] = 1
    return netlink.RouteReplace(&netlink.Route{
        LinkIndex: link.Attrs().Index,
        Dst: &net.IPNet{
            IP:   []byte{0, 0, 0, 0},
            Mask: []byte{0, 0, 0, 0},
        },
        Gw: gw,
    })
}