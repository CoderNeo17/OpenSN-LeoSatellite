#!/bin/bash
Xvfb :1 -screen 0 1280x800x24 &
sleep 1
openbox &
x11vnc -display :1 -forever -nopw -shared &
websockify --web /usr/share/novnc 6080 localhost:5900