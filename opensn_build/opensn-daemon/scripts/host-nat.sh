#!/bin/bash
# Host side — run once before simulation
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o wlp1s0 -j MASQUERADE
sudo iptables -A FORWARD -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A FORWARD -d 10.0.0.0/8 -j ACCEPT