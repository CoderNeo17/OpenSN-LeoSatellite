# FROM build-base:latest

# # Only pip3 and playwright package
# RUN apt-get update && apt-get install -y python3-pip && \
#     rm -rf /var/lib/apt/lists/*

# RUN pip3 install playwright
# RUN playwright install-deps
# RUN playwright install firefox

# COPY home/script.py /home/script.py

FROM build-base:latest

# Copy the firefox.tar.xz file into the container
COPY firefox.tar.xz /tmp/firefox.tar.xz

RUN apt-get update && apt-get install -y \
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
    ca-certificates \
    python3 \
    python3-pip \
    dbus \
    dbus-x11 \
    pulseaudio \
    alsa-utils \
    gosu \
    && rm -rf /var/lib/apt/lists/*


ENV DISPLAY=:0

RUN tar -xJf /tmp/firefox.tar.xz -C /opt && \
    ln -s /opt/firefox/firefox /usr/local/bin/firefox && \
    rm /tmp/firefox.tar.xz

RUN useradd -u 1000 -m user && \
    mkdir -p /home/user && \
    chown -R 1000:1000 /home/user

ENV HOME=/home/user
WORKDIR /home/user

COPY scripts/entrypoint /Workspace/entrypoint
COPY home /home
RUN chmod +x /Workspace/entrypoint
CMD [ "/Workspace/entrypoint"]
