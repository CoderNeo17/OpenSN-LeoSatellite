package frr

import (
	"fmt"
	"os"

	"github.com/sirupsen/logrus"
)

var CommandBatchPath = "/etc/frr/batch.txt"

func InitOspf() error {
	logrus.Info("Initializing OSPF base configuration")

	batch := `
bfd

router ospf
 area 1 stub no-summary
 timers throttle spf 0 20 100
 area 1 range 10.2.0.0/16 not-advertise
 area 1 range 10.0.0.0/16 not-advertise
 area 1 range 10.1.0.0/16 advertise
`

	confFile, err := os.Create(CommandBatchPath)
	if err != nil {
		logrus.Errorf("Failed to create batch file: %v", err)
		return err
	}
	defer confFile.Close()

	if _, err = confFile.Write([]byte(batch)); err != nil {
		logrus.Errorf("Failed to write batch config: %v", err)
		return err
	}

	if err := WriteOspfConfig(CommandBatchPath); err != nil {
		logrus.Errorf("Failed to apply OSPF config: %v", err)
		return err
	}

	logrus.Info("OSPF base configuration applied successfully")
	return nil
}

func EnableOspfOnInterface(ifName string, passive bool, area int) error {
	logrus.Infof("Configuring OSPF on interface %s (passive=%v)", ifName, passive)

	var cmd string
	if passive {
		cmd = fmt.Sprintf(`
interface %s
 ip ospf area 1
 ip ospf passive
 ip ospf network point-to-point
 ip ospf hello-interval 1
 ip ospf dead-interval 3
`, ifName)
	} else {
		cmd = fmt.Sprintf(`
interface %s
 ip ospf area %d
 ip ospf network point-to-point
 ip ospf dead-interval minimal hello-multiplier 5
 ip ospf bfd
`, ifName, area)
	}

	confFile, err := os.Create(CommandBatchPath)
	if err != nil {
		logrus.Errorf("Failed to create batch file for %s: %v", ifName, err)
		return err
	}
	defer confFile.Close()

	if _, err = confFile.Write([]byte(cmd)); err != nil {
		logrus.Errorf("Failed to write config for %s: %v", ifName, err)
		return err
	}

	if err := WriteOspfConfig(CommandBatchPath); err != nil {
		logrus.Errorf("Failed to apply OSPF config for %s: %v", ifName, err)
		return err
	}

	logrus.Infof("OSPF enabled on interface %s", ifName)
	return nil
}
