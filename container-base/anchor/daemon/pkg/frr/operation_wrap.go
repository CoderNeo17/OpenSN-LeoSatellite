package frr

import (
	"fmt"
	"os"
	"satellite/model"

	"github.com/sirupsen/logrus"
)

var batchDefault = `
router ospf
  redistribute connected
  default-information originate
%s`

var CommandBatchPath = "/etc/frr/batch.txt"

func InitConfigBatch(links []*model.LinkInfo) error {
    var networks string
    for _, v := range links {
        networks += fmt.Sprintf("  network %s area 0.0.0.0\n", v.V4Addr)
    }
    batch := fmt.Sprintf(batchDefault, networks)

    confFile, err := os.Create(CommandBatchPath)
    if err != nil {
        logrus.Errorf("Create FRR Configuration Error: %s", err.Error())
        return err
    }
    defer confFile.Close()
    if _, err = confFile.Write([]byte(batch)); err != nil {
        logrus.Errorf("Write FRR Configuration Error: %s", err.Error())
        return err
    }
    return WriteOspfConfig(CommandBatchPath)
}
