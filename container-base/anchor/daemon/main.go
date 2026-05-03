package main

import (
	"os"
	"os/signal"
	"anchor/config"
	"anchor/data"
	"anchor/pkg/configure"
	// "anchor/pkg/frr"
	"anchor/pkg/ifconfig"
	"anchor/pkg/route"
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
