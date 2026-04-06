#!/usr/bin/env bash
set -euo pipefail

# eyeon-parse: wrapper for "eyeon parse -o O -t N DIR" inside the container.
#
# Usage:
#   eyeon-parse UTIL_CD DIR [THREADS]
#
# Environment overrides (optional):
#   EYEON_IMAGE        (default: ghcr.io/llnl/peyeon:latest)
#   EYEON_OUTPUT_ROOT  (default: $HOME/data/eyeon)
#   EYEON_THREADS      (default: 4)

IMAGE="${EYEON_IMAGE:-ghcr.io/llnl/peyeon:latest}"
OUTPUT_ROOT="${EYEON_OUTPUT_ROOT:-$HOME/data/eyeon/dev}"
DEFAULT_THREADS="${EYEON_THREADS:-4}"

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $(basename "$0") UTIL_CD DIR [THREADS]" >&2
  exit 2
fi

UTIL_CD="$1"
DIR="$2"
THREADS="${3:-$DEFAULT_THREADS}"

if [[ ! -d "$DIR" ]]; then
  echo "DIR is not a directory: $DIR" >&2
  exit 2
fi

if ! [[ "$THREADS" =~ ^[0-9]+$ ]] || [[ "$THREADS" -lt 1 ]]; then
  echo "THREADS must be a positive integer, got: $THREADS" >&2
  exit 2
fi

ts="$(date -u +'%Y%m%dT%H%M%SZ')"
O="${ts}_${UTIL_CD}"

mkdir -p "$OUTPUT_ROOT/$O"

exec docker run --rm \
  -v "$DIR:/source:ro" \
  -v "$OUTPUT_ROOT:/workdir:rw,Z" \
  "$IMAGE" \
  eyeon parse -o "/workdir/$O" -t "$THREADS" /source