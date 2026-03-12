#!/bin/bash
# Generate and apply alembic migrations
cd "$(dirname "$0")/../backend" || exit 1

if [ "$1" = "generate" ]; then
    shift
    uv run alembic revision --autogenerate -m "${1:-auto}"
elif [ "$1" = "upgrade" ]; then
    uv run alembic upgrade head
elif [ "$1" = "downgrade" ]; then
    uv run alembic downgrade -1
else
    echo "Usage: $0 {generate [message]|upgrade|downgrade}"
fi
