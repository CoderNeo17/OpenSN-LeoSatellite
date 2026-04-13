FROM build-base:latest

COPY --from=selenium/standalone-chrome:4.10.0-20230607 /usr/bin/google-chrome /usr/bin/google-chrome
COPY --from=selenium/standalone-chrome:4.10.0-20230607 /usr/bin/chromedriver /usr/bin/chromedriver
COPY --from=selenium/standalone-chrome:4.10.0-20230607 /opt/google /opt/google
COPY --from=selenium/standalone-chrome:4.10.0-20230607 /usr/share/fonts /usr/share/fonts

RUN apt-get update && apt-get install -y \
    python3-pip \
    libglib2.0-0 \
    libnss3 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxshmfence1 \
    libgles2 \
    libegl1 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y dbus && \
    rm -rf /var/lib/apt/lists/*

# RUN pip3 install selenium

ENV DISPLAY=:0

# COPY script.py /script.py

# CMD ["python3", "/script.py"]
CMD ["bash"]