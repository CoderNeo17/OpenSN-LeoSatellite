package frr

import (
	"fmt"
	"ground/model"
	"os"
	"sync"

	"github.com/sirupsen/logrus"
)

// CommandBatch must start with "configure terminal" so vtysh enters config
// mode before issuing OSPF sub-commands.
var CommandBatch = `configure terminal
router ospf
 redistribute connected
`
var CommandBatchPath = "/etc/frr/batch.txt"

var mu sync.Mutex
var currentNetwork string

// InitConfigBatch writes a vtysh batch file that adds the supplied link
// networks to OSPF area 0 and commits it.  It removes any previously
// advertised network first so stale routes are not left in the RIB after
// a satellite handover.
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
	batch += "end\n"

	confFile, err := os.Create(CommandBatchPath)
	if err != nil {
		logrus.Errorf("Create FRR Configuration Error: %s", err.Error())
		return err
	}
	_, err = confFile.Write([]byte(batch))
	confFile.Close() // close before exec so vtysh sees the full file
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