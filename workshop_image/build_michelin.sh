#!/bin/bash

# Temporary build script for testing purposes

# Clone Michelin certs from local gitlab

git clone https://gitlab.michelin.com/software_engineering/platform_components/DEV/bib-certificates ./install_scripts/michelin_certs

# Build image in michelin mode

docker build -t workshop_ensimag:test --build-arg michelin_build="true"  --progress=plain .