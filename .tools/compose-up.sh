#!/bin/bash
# Build and start all services via podman compose
cd "$(dirname "$0")/.." || exit 1
exec podman compose -f dev.docker-compose.yaml up --build
