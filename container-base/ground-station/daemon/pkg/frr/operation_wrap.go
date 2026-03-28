package frr

import (
	"fmt"
	"ground/model"
	"os"
	"sync"

	"github.com/sirupsen/logrus"
)

// When using vtysh -f (batch file mode), vtysh automatically wraps the
// file in a configure/end transaction. Do NOT include "configure terminal"
// or "end" in the file — they are unknown commands in this context and
// will cause vtysh to return exit status 2 and crash ospfd.
var CommandBatch = `router ospf
 redistribute connected
`
var CommandBatchPath = "/etc/frr/batch.txt"

var mu sync.Mutex
var currentNetwork string

func InitConfigBatch(links []*model.LinkInfo) error {
	mu.Lock()
	defer mu.Unlock()

	batch := CommandBatch
	for _, v := range links {
		if v == nil {
			continue
		}
		if currentNetwork != "" && currentNetwork != v.V4Addr {
			if err := RemoveOspfNetwork(currentNetwork); err != nil {
				logrus.Warnf("RemoveOspfNetwork %s: %s", currentNetwork, err.Error())
			}
			currentNetwork = ""
		}
		batch += fmt.Sprintf(" network %s area 0.0.0.0\n", v.V4Addr)
		currentNetwork = v.V4Addr
	}

	confFile, err := os.Create(CommandBatchPath)
	if err != nil {
		logrus.Errorf("Create FRR Configuration Error: %s", err.Error())
		return err
	}
	_, err = confFile.Write([]byte(batch))
	confFile.Close()
	if err != nil {
		logrus.Errorf("Write FRR Configuration Error: %s", err.Error())
		return err
	}

	if err = WriteOspfConfig(CommandBatchPath); err != nil {
		logrus.Errorf("Write FRR Configuration to VTY Error: %s", err.Error())
		return err
	}
	return nil
}