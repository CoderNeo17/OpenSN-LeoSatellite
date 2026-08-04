FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    xz-utils \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libx11-xcb1 \
    libxt6 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libatk1.0-0 \
    libcups2 \
    libnss3 \
    libxss1 \
    libxkbcommon0 \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libatk-bridge2.0-0 \
    libgbm1 \
    libu2f-udev \
    fonts-liberation \
    xdg-utils \
    python3 \
    python3-pip \
    dbus \
    dbus-x11 \
    pulseaudio \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

ENV DISPLAY=:0

RUN wget -q -O /tmp/chrome.deb \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && ln -sf /usr/bin/google-chrome-stable /usr/bin/chrome

RUN useradd -u 1000 -m user && \
    mkdir -p /home/user && \
    chown -R 1000:1000 /home/user

ENV HOME=/home/user
WORKDIR /home/user

CMD [ "/bin/bash" ]