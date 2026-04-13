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
    && rm -rf /var/lib/apt/lists/*

ENV DISPLAY=:0

RUN tar -xJf /tmp/firefox.tar.xz -C /opt && \
    ln -s /opt/firefox/firefox /usr/local/bin/firefox && \
    rm /tmp/firefox.tar.xz

# CMD ["bash"]

CMD [ "/Workspace/entrypoint"]