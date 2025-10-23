FROM freeswitch/freeswitch:latest

# Ensure curl is available for the dialplan system curl usage and other tools
USER root
RUN apt-get update \
    && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration (the docker-compose mounts the conf dir at runtime)
WORKDIR /etc/freeswitch

ENV FREESWITCH_ESL_PASSWORD=ClueCon

USER freeswitch

CMD ["/usr/bin/freeswitch", "-nonat"]
