FROM build-base

RUN apt update && apt install -y \
    chromium-browser \
    chromium-chromedriver \
    curl \
    wget \
    dnsutils \
    net-tools \
    python3 \
    python3-pip \
    --no-install-recommends

RUN pip3 install selenium requests

COPY scripts/entrypoint /Workspace/entrypoint
RUN chmod +x /Workspace/entrypoint
CMD ["/Workspace/entrypoint"]