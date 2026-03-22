package nat

import (
	"os/exec"

	"github.com/sirupsen/logrus"
)

func InitNAT() {
	// Find the eth0 interface — Docker's default external-facing interface
	cmds := [][]string{
		{"sysctl", "-w", "net.ipv4.ip_forward=1"},
		{"iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"},
		{"iptables", "-A", "FORWARD", "-j", "ACCEPT"},
	}
	for _, args := range cmds {
		out, err := exec.Command(args[0], args[1:]...).CombinedOutput()
		if err != nil {
			logrus.Errorf("NAT init %v error: %s — %s", args, err.Error(), string(out))
		}
	}
	logrus.Info("NAT gateway initialized")
}
