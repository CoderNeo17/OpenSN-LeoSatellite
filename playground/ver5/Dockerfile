# FROM build-base:latest

# # Only pip3 and playwright package
# RUN apt-get update && apt-get install -y python3-pip && \
#     rm -rf /var/lib/apt/lists/*

# RUN pip3 install playwright
# RUN playwright install-deps
# RUN playwright install firefox

# COPY home/script.py /home/script.py

FROM build-base:latest


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
    && rm -rf /var/lib/apt/lists/*


ENV DISPLAY=:0

RUN apt-get update && apt-get install -y wget gnupg
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
RUN apt-get update && apt-get install -y google-chrome-stable

RUN useradd -u 1000 -m user && \
    mkdir -p /home/user && \
    chown -R 1000:1000 /home/user

ENV HOME=/home/user
WORKDIR /home/user

# CMD ["bash"]

# CMD [ "/Workspace/entrypoint"]

CMD [ "bash"]
