#!/bin/bash
# Start the dev server with DEV_MODE enabled
cd "$(dirname "$0")/../backend" || exit 1
DEV_MODE=true exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
