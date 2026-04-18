FROM build-base

RUN apt update && apt install -y \
    iptables

COPY scripts/entrypoint /Workspace/entrypoint
RUN chmod +x /Workspace/entrypoint
CMD [ "/Workspace/entrypoint"]
