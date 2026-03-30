#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="$SCRIPT_DIR/../VERSION"

version=$(cat "$VERSION_FILE" | tr -d '[:space:]')
major="${version%%.*}"
minor="${version#*.}"

case "${1:-}" in
  major)
    major=$((major + 1))
    minor=0
    echo "$major.$minor" > "$VERSION_FILE"
    ;;
  minor)
    minor=$((minor + 1))
    echo "$major.$minor" > "$VERSION_FILE"
    ;;
  "") ;;
  *)
    echo "Usage: $0 [major|minor]" >&2
    exit 1
    ;;
esac

short_sha=$(git -C "$SCRIPT_DIR/.." rev-parse --short HEAD 2>/dev/null || echo "unknown")
version_string="$major.$minor.$short_sha"
echo "$version_string"

git -C "$SCRIPT_DIR/.." tag "v$major.$minor" 2>/dev/null || git -C "$SCRIPT_DIR/.." tag -f "v$major.$minor"
