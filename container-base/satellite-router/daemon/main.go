package main

import (
	"os"
	"os/signal"
	"satellite/config"
	"satellite/data"
	"satellite/pkg/configure"
	// "satellite/pkg/frr"
	"satellite/pkg/ifconfig"
	"satellite/pkg/route"
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
