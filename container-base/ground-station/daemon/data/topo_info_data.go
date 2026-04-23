package data

import (
	"encoding/json"
	"os"
	"ground-station/config"
	"ground-station/model"
	"time"

	"github.com/sirupsen/logrus"
)

var TopoInfo model.TopoInfo

func InitTopoInfoData() {
    for {
        fd, err := os.Open(config.TopoInfoPath)
        if err != nil {
            logrus.Errorf("Open Topo Infomation File Error: %s", err.Error())
            time.Sleep(time.Second)
            continue
        }
        decoder := json.NewDecoder(fd)
        err = decoder.Decode(&TopoInfo)
        fd.Close()
        if err != nil {
            logrus.Errorf("Decode Json Topo Infomation Error: %s", err.Error())
        }
        return
    }
}
