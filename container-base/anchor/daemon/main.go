package main

import (
	"anchor/config"
	"anchor/data"
	"anchor/pkg/configure"
	"anchor/pkg/ifconfig"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	data.InitTopoInfoData()
	ifconfig.InitInterfaceWatcher()
	configure.InitConfigurationWatcher(config.TopoInfoPath)
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan
}
