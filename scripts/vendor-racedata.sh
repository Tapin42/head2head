#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RACEDATA_SOURCE="${RACEDATA_PATH:-$ROOT/../racedata}"

if [[ ! -d "$RACEDATA_SOURCE" ]]; then
  echo "racedata source directory not found: $RACEDATA_SOURCE" >&2
  echo "Set RACEDATA_PATH to the racedata checkout path before running this script." >&2
  exit 1
fi

rm -rf "$ROOT/racedata"
cp -R "$RACEDATA_SOURCE" "$ROOT/racedata"
echo "Vendored racedata into head2head/racedata for Docker/Fly builds."
