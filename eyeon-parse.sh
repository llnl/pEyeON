#!/usr/bin/env bash
set -euo pipefail

# eyeon-parse: wrapper for "eyeon parse -o O -t N SOURCE" inside the container.
#
# All inputs can be provided by environment variables and/or command line args.
# Command line args take precedence over environment variables.
#
# Usage:
#   eyeon-parse [--util-cd UTIL_CD] [--dir SOURCE] [--threads THREADS] \
#               [--image IMAGE] [--dataset-path DATASET_PATH]
#   eyeon-parse UTIL_CD SOURCE [DATASET_PATH] [THREADS]
#
# Environment variables (optional):
#   EYEON_UTIL_CD
#   EYEON_SOURCE
#   EYEON_THREADS      (default: 8)
#   EYEON_IMAGE        (default: ghcr.io/llnl/peyeon:latest; override for dev/test images)
#   EYEON_DATASET_PATH (default: datasets.dataset_path from EyeOnData.toml)
#   EYEON_OWNER        (required when running as root unless passthrough is enabled)
#   EYEON_UID / EYEON_GID
#   EYEON_PASSTHROUGH_ROOT=1 (intentionally create root-owned outputs)
#
# Example dev image override:
#   EYEON_IMAGE=ghcr.io/llnl/peyeon-dev:dev-<sha> ./eyeon-parse.sh UTIL_CD SOURCE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="${SCRIPT_DIR}/EyeOnData.toml"

read_dataset_path_from_toml() {
  if [[ ! -f "$SETTINGS_FILE" ]]; then
    return 0
  fi

  awk '
    BEGIN { in_datasets = 0 }
    /^[[:space:]]*\[/ {
      in_datasets = ($0 ~ /^[[:space:]]*\[datasets\][[:space:]]*$/)
      next
    }
    in_datasets && /^[[:space:]]*dataset_path[[:space:]]*=/ {
      value = $0
      sub(/^[[:space:]]*dataset_path[[:space:]]*=[[:space:]]*/, "", value)
      sub(/[[:space:]]*(#.*)?$/, "", value)
      sub(/^"/, "", value)
      sub(/"$/, "", value)
      print value
      exit
    }
  ' "$SETTINGS_FILE"
}

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") [--util-cd UTIL_CD] [--dir SOURCE] [--threads THREADS] [--image IMAGE] [--dataset-path DATASET_PATH]
       $(basename "$0") UTIL_CD SOURCE [DATASET_PATH] [THREADS]

Command line args override environment variables.

Environment variables:
  EYEON_UTIL_CD
  EYEON_SOURCE
  EYEON_THREADS      Default: 8
  EYEON_IMAGE        Default: ghcr.io/llnl/peyeon:latest; override for dev/test images
  EYEON_DATASET_PATH Default: datasets.dataset_path from EyeOnData.toml
  EYEON_OWNER        Required when running as root unless passthrough is enabled
  EYEON_UID/GID      Explicit numeric owner override for runtime outputs
  EYEON_PASSTHROUGH_ROOT=1  Intentionally create root-owned outputs
EOF
}

resolve_owner_ids() {
  local owner="$1"

  if ! id "$owner" >/dev/null 2>&1; then
    echo "EYEON_OWNER does not exist: $owner" >&2
    exit 2
  fi

  HOST_UID="$(id -u "$owner")"
  HOST_GID="$(id -g "$owner")"
}

IMAGE="${EYEON_IMAGE:-ghcr.io/llnl/peyeon-dev:dev}"
DATASET_PATH="${EYEON_DATASET_PATH:-}"
UTIL_CD="${EYEON_UTIL_CD:-}"
SOURCE="${EYEON_SOURCE:-}"
THREADS="${EYEON_THREADS:-8}"
OWNER_OVERRIDE="${EYEON_OWNER:-}"
HOST_UID="${EYEON_UID:-}"
HOST_GID="${EYEON_GID:-}"
PASSTHROUGH_ROOT="${EYEON_PASSTHROUGH_ROOT:-0}"
UTIL_CD_FLAG_SET=0
SOURCE_FLAG_SET=0
THREADS_FLAG_SET=0

POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --util-cd)
      if [[ $# -lt 2 || "$2" == -* ]]; then
        echo "Missing value for --util-cd" >&2
        usage
        exit 2
      fi
      UTIL_CD="${2:-}"
      UTIL_CD_FLAG_SET=1
      shift 2
      ;;
    --dir)
      if [[ $# -lt 2 || "$2" == -* ]]; then
        echo "Missing value for --dir" >&2
        usage
        exit 2
      fi
      SOURCE="${2:-}"
      SOURCE_FLAG_SET=1
      shift 2
      ;;
    --threads)
      if [[ $# -lt 2 || "$2" == -* ]]; then
        echo "Missing value for --threads" >&2
        usage
        exit 2
      fi
      THREADS="${2:-}"
      THREADS_FLAG_SET=1
      shift 2
      ;;
    --image)
      if [[ $# -lt 2 || "$2" == -* ]]; then
        echo "Missing value for --image" >&2
        usage
        exit 2
      fi
      IMAGE="${2:-}"
      shift 2
      ;;
    --dataset-path)
      if [[ $# -lt 2 || "$2" == -* ]]; then
        echo "Missing value for --dataset-path" >&2
        usage
        exit 2
      fi
      DATASET_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      POSITIONAL+=("$@")
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [[ ${#POSITIONAL[@]} -gt 4 ]]; then
  usage
  exit 2
fi

if [[ $UTIL_CD_FLAG_SET -eq 0 && ${#POSITIONAL[@]} -ge 1 ]]; then
  UTIL_CD="${POSITIONAL[0]}"
fi

if [[ $SOURCE_FLAG_SET -eq 0 && ${#POSITIONAL[@]} -ge 2 ]]; then
  SOURCE="${POSITIONAL[1]}"
fi

if [[ ${#POSITIONAL[@]} -ge 3 ]]; then
  if [[ $THREADS_FLAG_SET -eq 0 && "${POSITIONAL[2]}" =~ ^[0-9]+$ ]]; then
    THREADS="${POSITIONAL[2]}"
  else
    DATASET_PATH="${POSITIONAL[2]}"
  fi
fi

if [[ $THREADS_FLAG_SET -eq 0 && ${#POSITIONAL[@]} -ge 4 ]]; then
  THREADS="${POSITIONAL[3]}"
fi

if [[ -z "$UTIL_CD" || -z "$SOURCE" ]]; then
  usage
  exit 2
fi

if [[ -z "$DATASET_PATH" ]]; then
  DATASET_PATH="$(read_dataset_path_from_toml)"
fi

if [[ -z "$DATASET_PATH" ]]; then
  DATASET_PATH=$HOME/data/eyeon
  echo "DATASET_PATH defaulting to $DATASET_PATH. To override, set datasets.dataset_path in EyeOnData.toml, EYEON_DATASET_PATH, or --dataset-path." >&2
fi

if [[ ! -d "$SOURCE" ]]; then
  echo "SOURCE is not a directory: $SOURCE" >&2
  exit 2
fi

if ! [[ "$THREADS" =~ ^[0-9]+$ ]] || [[ "$THREADS" -lt 1 ]]; then
  echo "THREADS must be a positive integer, got: $THREADS" >&2
  exit 2
fi

if [[ -n "$OWNER_OVERRIDE" && (-n "$HOST_UID" || -n "$HOST_GID") ]]; then
  echo "Set either EYEON_OWNER or EYEON_UID/EYEON_GID, not both." >&2
  exit 2
fi

if [[ -n "$OWNER_OVERRIDE" ]]; then
  resolve_owner_ids "$OWNER_OVERRIDE"
elif [[ -n "$HOST_UID" || -n "$HOST_GID" ]]; then
  if [[ -z "$HOST_UID" || -z "$HOST_GID" ]]; then
    echo "EYEON_UID and EYEON_GID must both be set together." >&2
    exit 2
  fi
elif [[ "$EUID" -eq 0 ]]; then
  if [[ "$PASSTHROUGH_ROOT" == "1" ]]; then
    HOST_UID=0
    HOST_GID=0
  else
    echo "Running as root requires EYEON_OWNER or EYEON_UID/EYEON_GID." >&2
    echo "Set EYEON_PASSTHROUGH_ROOT=1 to intentionally create root-owned outputs." >&2
    exit 2
  fi
else
  HOST_UID="$(id -u)"
  HOST_GID="$(id -g)"
fi

if ! [[ "$HOST_UID" =~ ^[0-9]+$ && "$HOST_GID" =~ ^[0-9]+$ ]]; then
  echo "Resolved runtime UID/GID must be numeric, got: $HOST_UID:$HOST_GID" >&2
  exit 2
fi

# Create a structured name for the parsed batch of data using a timestamp and the UTIL_CD.
ts="$(date -u +'%Y%m%dT%H%M%SZ')"
O="${ts}_${UTIL_CD}"

mkdir -p "$DATASET_PATH/$O"

# Removed rm for testing...
exec docker run \
  -e "EYEON_UID=$HOST_UID" \
  -e "EYEON_GID=$HOST_GID" \
  -v "$SOURCE:/source:ro" \
  -v "$DATASET_PATH:/workdir:rw,Z" \
  "$IMAGE" \
  eyeon parse -o "/workdir/$O" -t "$THREADS" /source
