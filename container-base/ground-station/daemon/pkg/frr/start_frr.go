package frr

import (
	"fmt"
	"os"
	"os/exec"
	"time"

	"github.com/sirupsen/logrus"
)

func StartFrr() error {
	cmd := exec.Command("service", "frr", "start")
	if err := cmd.Run(); err != nil {
		logrus.Errorf("Start FRR Error: %s", err.Error())
		return err
	}
	if err := WaitForOspfd(30 * time.Second); err != nil {
		return err
	}
	return nil
}

// WaitForOspfd waits until ospfd's VTY socket exists on disk.
// This is the correct readiness signal — the socket is created by ospfd
// only after it has fully initialised and is ready to accept connections.
// Probing with vtysh itself causes watchfrr to register a connection
// attempt against a dead daemon and trigger another restart cycle.
func WaitForOspfd(timeout time.Duration) error {
	// ospfd creates this socket when it is ready to accept vtysh connections.
	const ospfdSocket = "/var/run/frr/ospfd.vty"
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(ospfdSocket); err == nil {
			// Socket exists — give ospfd one more second to finish binding
			// its internal state before we push config.
			time.Sleep(time.Second)
			logrus.Info("ospfd is up and ready")
			return nil
		}
		logrus.Info("Waiting for ospfd to be ready...")
		time.Sleep(time.Second)
	}
	return fmt.Errorf("ospfd did not become ready within %s", timeout)
}

func isOspfdRunning() bool {
	const ospfdSocket = "/var/run/frr/ospfd.vty"
	_, err := os.Stat(ospfdSocket)
	return err == nil
}

func StartZebra() error {
	cmd := exec.Command(
		"/usr/lib/frr/zebra", "-d",
		"-F", "traditional",
		"-A", "127.0.0.1",
		"-s", "90000000",
	)
	if err := cmd.Run(); err != nil {
		logrus.Errorf("Start Zebra Error: %s", err.Error())
		return err
	}
	return nil
}

func StartOspfd() error {
	cmd := exec.Command(
		"/usr/lib/frr/ospfd", "-d",
		"-F", "traditional",
		"-A", "127.0.0.1",
	)
	if err := cmd.Run(); err != nil {
		logrus.Errorf("Start Ospfd Error: %s", err.Error())
		return err
	}
	return nil
}

func RemoveOspfNetwork(network string) error {
	if err := WaitForOspfd(15 * time.Second); err != nil {
		logrus.Warnf("RemoveOspfNetwork: ospfd not ready: %s", err.Error())
		return err
	}
	out, err := exec.Command("/usr/bin/vtysh",
		"-c", "configure terminal",
		"-c", "router ospf",
		"-c", fmt.Sprintf("no network %s area 0.0.0.0", network),
		"-c", "end",
	).CombinedOutput()
	if err != nil {
		logrus.Warnf("Remove network %s error: %s — %s", network, err.Error(), string(out))
	}
	return err
}

// WriteOspfConfig applies a vtysh batch file.
// The file must NOT contain "configure terminal" or "end" — vtysh -f
// wraps the file in its own config transaction automatically. Including
// those commands causes "% Unknown command" errors and crashes ospfd.
func WriteOspfConfig(batchPath string) error {
	if err := WaitForOspfd(15 * time.Second); err != nil {
		logrus.Errorf("WriteOspfConfig: ospfd not ready: %s", err.Error())
		return err
	}
	out, err := exec.Command("/usr/bin/vtysh", "-f", batchPath).CombinedOutput()
	if err != nil {
		logrus.Errorf("Config Ospfd Error: %s — %s", err.Error(), string(out))
		return err
	}
	return nil
}