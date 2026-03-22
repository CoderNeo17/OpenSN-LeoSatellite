package main

import (
	"user/config"
	"user/data"
	"user/pkg/configure"
	"user/pkg/ifconfig"
	"os"
	"os/signal"
	"syscall"
)

func main() {
    data.InitTopoInfoData()
    os.WriteFile("/etc/resolv.conf", []byte("nameserver 8.8.8.8\n"), 0644)
    ifconfig.InitInterfaceWatcher()
    configure.InitConfigurationWatcher(config.TopoInfoPath)
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
    <-sigChan
}
