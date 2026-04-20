FROM build-base

RUN apt update && apt install -y \
    iptables \
    conntrack \
    conntrackd 

COPY scripts /Workspace/
RUN chmod +x /Workspace/entrypoint
CMD [ "/Workspace/entrypoint"]
