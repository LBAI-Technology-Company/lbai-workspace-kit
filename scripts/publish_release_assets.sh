#!/usr/bin/env sh
set -eu

TAG="${1:-}"
if [ -z "$TAG" ]; then
  printf '%s\n' "usage: scripts/publish_release_assets.sh vX.Y.Z" >&2
  exit 2
fi

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"

for file in install.sh install.ps1 install-bootstrap.ps1; do
  if [ ! -f "$ROOT/$file" ]; then
    printf '%s\n' "missing required file: $ROOT/$file" >&2
    exit 2
  fi
done

gh release upload "$TAG" \
  "$ROOT/install.sh" \
  "$ROOT/install.ps1" \
  "$ROOT/install-bootstrap.ps1" \
  --clobber

printf '%s\n' "Uploaded installer assets to release $TAG."
