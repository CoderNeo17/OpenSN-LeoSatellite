package main

import (
	"os"
	"os/signal"
	"ground-station/config"
	"ground-station/data"
	"ground-station/pkg/configure"
	// "ground-station/pkg/frr"
	"ground-station/pkg/ifconfig"
	"ground-station/pkg/route"
	"syscall"
)

func main() {
	data.InitTopoInfoData()
	// err := frr.StartFrr()
	// if err != nil {
	// 	panic(err)
	// }
	ifconfig.InitInterfaceWatcher()
	configure.InitConfigurationWatcher(config.TopoInfoPath)
	route.InitDijkstra()
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan
}
