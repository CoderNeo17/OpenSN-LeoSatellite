FROM build-base

RUN touch /etc/frr/bfdd.conf && \
    chown frr:frr /etc/frr/bfdd.conf && \
    chmod 640 /etc/frr/bfdd.conf
COPY materials/daemons /etc/frr/daemons
COPY scripts/entrypoint /Workspace/entrypoint
RUN chmod +x /Workspace/entrypoint
CMD [ "/Workspace/entrypoint"]
