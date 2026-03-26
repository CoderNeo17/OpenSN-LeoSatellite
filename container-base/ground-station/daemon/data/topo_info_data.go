package data

import (
	"encoding/json"
	"ground/config"
	"ground/model"
	"os"
	"time"

	"github.com/sirupsen/logrus"
)

var TopoInfo model.TopoInfo

func InitTopoInfoData() {
	for {
		fd, err := os.Open(config.TopoInfoPath)
		if err != nil {
			logrus.Errorf("Open Topo Information File Error: %s", err.Error())
			time.Sleep(time.Second)
			continue
		}
		decoder := json.NewDecoder(fd)
		err = decoder.Decode(&TopoInfo)
		fd.Close()
		if err != nil {
			logrus.Errorf("Decode Json Topo Information Error: %s", err.Error())
			// File exists but is malformed — keep retrying until it is valid.
			time.Sleep(time.Second)
			continue
		}
		return
	}
}