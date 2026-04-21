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
router ospf
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

func EnableOspfOnInterface(ifName string, passive bool) error {
    logrus.Infof("Configuring OSPF on interface %s (passive=%v)", ifName, passive)

    var cmd string
    if passive {
        cmd = fmt.Sprintf(`
interface %s
 ip ospf area 0
 ip ospf passive
`, ifName)
    } else {
        cmd = fmt.Sprintf(`
interface %s
 ip ospf area 0
`, ifName)
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
