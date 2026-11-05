#!/bin/bash

xhost +local:docker

if [ $# -ne 1 ]; then
    echo "Usage: $0 <container_name>"
    exit 1
fi

CONTAINER="$1"

# Fix runtime directory permissions
docker exec -u root "$CONTAINER" bash -c '
mkdir -p /run/user/1000
chown -R 1000:1000 /run/user/1000
chmod 700 /run/user/1000

chmod +x ./../start_dbus.sh
chown 1000:1000 ./../start_dbus.sh
'

# Start an interactive shell as user 1000
docker exec -it -u 1000 "$CONTAINER" bash -c '
export XDG_RUNTIME_DIR=/run/user/1000

mkdir -p "$XDG_RUNTIME_DIR/dconf"

echo "Starting dbus..."
./../start_dbus.sh

eval "$(dbus-launch --sh-syntax)"

echo "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"
echo "Starting Firefox..."

firefox --no-remote
'