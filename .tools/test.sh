#!/bin/bash
# Run tests
cd "$(dirname "$0")/../backend" || exit 1
DEV_MODE=true uv run pytest "$@"
