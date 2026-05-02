package main

import (
	"os"
	"os/signal"
	"satellite/config"
	"satellite/data"
	"satellite/pkg/configure"
	"satellite/pkg/route"
	"satellite/pkg/ifconfig"
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
