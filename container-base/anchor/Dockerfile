FROM build-base

RUN apt update && apt install -y \
    iptables

COPY materials/daemons /etc/frr/daemons
COPY scripts/entrypoint /Workspace/entrypoint
RUN chmod +x /Workspace/entrypoint
CMD [ "/Workspace/entrypoint"]