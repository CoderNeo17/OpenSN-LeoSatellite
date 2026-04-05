FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1

# Use India mirror for faster downloads
RUN sed -i 's|http://archive.ubuntu.com|http://in.archive.ubuntu.com|g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates \
    xvfb x11vnc openbox \
    python3 python3-pip \
    novnc websockify \
    libgtk-3-0 libdbus-glib-1-2 libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

# Firefox direct versioned URL
RUN wget --no-verbose --tries=3 \
        "https://releases.mozilla.org/pub/firefox/releases/126.0/linux-x86_64/en-US/firefox-126.0.tar.bz2" \
        -O /tmp/firefox.tar.bz2 && \
    tar -xjf /tmp/firefox.tar.bz2 -C /opt && \
    ln -s /opt/firefox/firefox /usr/local/bin/firefox && \
    rm /tmp/firefox.tar.bz2

RUN pip3 install playwright selenium && \
    python3 -m playwright install firefox && \
    python3 -m playwright install-deps

RUN wget --tries=3 https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz \
    && tar -xzf geckodriver*.tar.gz -C /usr/local/bin \
    && rm geckodriver*.tar.gz

RUN ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html || true

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5900 6080
CMD ["/entrypoint.sh"]