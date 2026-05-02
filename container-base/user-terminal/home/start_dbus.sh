#!/bin/bash

mkdir -p /run/user/1000
chown user:user /run/user/1000
chmod 700 /run/user/1000

dbus-daemon --session --address=unix:path=/run/user/1000/bus --fork
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus