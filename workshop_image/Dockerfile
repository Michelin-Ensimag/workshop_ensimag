FROM ubuntu:22.04

ARG michelin_build=false

COPY code /workshop

COPY install_scripts /install_scripts

ENV TZ=Europe/Paris
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt


RUN if [ "$michelin_build" = "true" ]; then /install_scripts/pre_michelin_build.sh; fi \
    && DEBIAN_FRONTEND=noninteractive apt-get update && apt-get upgrade \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata \
    && echo $TZ > /etc/timezone \
    && apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    curl \
    nano vim \
    unzip \
    && if [ "$michelin_build" = "true" ]; then pip config set global.index-url "https://artifactory.michelin.com/api/pypi/pypi/simple"; fi \
    && pip install "ansible-core>=2.17.0" "ansible" && pip install -r /workshop/requirements.txt \
    && if [ "$michelin_build" = "true" ]; then /install_scripts/post_michelin_build.sh; fi \
    && rm -r /install_scripts

# Setup node
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash -

# Installe Node.js
RUN apt-get update
RUN apt-get install -y nodejs


ENTRYPOINT [ "tail", "-f", "/dev/null" ]
