#!/bin/bash

# Undo all specific Michelin configuration

pip config set global.index-url "https://pypi.org/simple"
mv /etc/apt/sources.list.bak /etc/apt/sources.list

# Remove Michelin certificates

rm /usr/local/share/ca-certificates/*
update-ca-certificates