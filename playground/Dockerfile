FROM build-base:latest

# # Copy Firefox from local image (no download)
# COPY --from=jlesage/firefox:latest /usr/bin/firefox /usr/bin/firefox
# COPY --from=jlesage/firefox:latest /usr/lib/firefox /usr/lib/firefox

# Only pip3 and playwright package (no install-deps, no install firefox)
RUN apt-get update && apt-get install -y python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install playwright
RUN playwright install-deps
RUN playwright install firefox

# Tell playwright where Firefox is instead of downloading its own
# ENV PLAYWRIGHT_FIREFOX_EXECUTABLE_PATH=/usr/bin/firefox

COPY script.py /script.py

CMD ["bash"]