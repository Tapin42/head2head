#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$ROOT/racedata"
cp -R "$ROOT/../racedata" "$ROOT/racedata"
echo "Vendored racedata into head2head/racedata for Docker/Fly builds."
