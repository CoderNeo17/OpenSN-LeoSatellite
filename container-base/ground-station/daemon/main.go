package main

import (
	"ground/config"
	"ground/data"
	"ground/pkg/configure"
	"ground/pkg/ifconfig"
	"ground/pkg/frr"
	"ground/pkg/nat"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	data.InitTopoInfoData()
	nat.InitNAT()
	err := frr.StartFrr()
    if err != nil {
        panic(err)
    }
	ifconfig.InitInterfaceWatcher()
	configure.InitConfigurationWatcher(config.TopoInfoPath)
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan
}
