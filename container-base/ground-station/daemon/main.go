package main

import (
	"os"
	"os/signal"
	"ground-station/config"
	"ground-station/data"
	"ground-station/pkg/configure"
	"ground-station/pkg/route"
	"ground-station/pkg/ifconfig"
	"syscall"
)

func main() {
	data.InitTopoInfoData()
	// err := frr.StartFrr()
	// if err != nil {
	// 	panic(err)
	// }
	ifconfig.InitInterfaceWatcher()
	route.InitDijkstra()
	configure.InitConfigurationWatcher(config.TopoInfoPath)
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan
}
