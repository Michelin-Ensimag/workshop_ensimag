#!/bin/bash

# Configure Michelin's Artifactory as a source for APT

mv /etc/apt/sources.list /etc/apt/sources.list.bak
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy main restricted" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy-updates main restricted" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy universe" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy-updates universe" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy multiverse" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy-updates multiverse" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy-security main restricted" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy-security universe" >> /etc/apt/sources.list
echo "deb https://artifactory.michelin.com/artifactory/ubuntu-archive-remote/ jammy-security multiverse" >> /etc/apt/sources.list

# Temporary configure apt to ignore SSL certificates to install update-ca-certificates

echo "Acquire::https::Verify-Peer "false";" >> /etc/apt/apt.conf.d/ignore-ssl
echo "Acquire::https::Verify-Host "false";" >> /etc/apt/apt.conf.d/ignore-ssl

# Install update-ca-certificates and disable file to ignore ssl configuration

apt-get update && apt-get install ca-certificates -y && rm /etc/apt/apt.conf.d/ignore-ssl

cp /install_scripts/michelin_certs/*.crt /usr/local/share/ca-certificates/
update-ca-certificates