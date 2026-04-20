#!/usr/bin/env bash
set -euo pipefail

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
Usage: $(basename "$0") [BATCH_DIR|DATASET_PATH ...]

Without an argument, the script resolves the dataset root the same way as eyeon-parse.sh,
finds the newest batch directory, and prints a short summary.

If one argument is provided:
  - a batch directory is summarized directly
  - otherwise the argument is treated as a dataset root and the newest batch is summarized

If multiple arguments are provided, each is treated as an explicit batch directory
and summarized in order. This supports shell globs like /data/eyeon/*string*.
EOF
}

resolve_default_dataset_path() {
  local dataset_path="${EYEON_DATASET_PATH:-}"

  if [[ -z "$dataset_path" ]]; then
    dataset_path="$(read_dataset_path_from_toml)"
  fi

  if [[ -z "$dataset_path" ]]; then
    dataset_path="$HOME/data/eyeon"
  fi

  printf '%s\n' "$dataset_path"
}

has_top_level_json() {
  local dir="$1"
  shopt -s nullglob
  local json_files=("$dir"/*.json)
  shopt -u nullglob
  (( ${#json_files[@]} > 0 ))
}

is_batch_name() {
  local dir="$1"
  local base="${dir##*/}"
  case "$base" in
    [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z_*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

latest_batch_dir() {
  local dataset_root="$1"
  local latest_dir=""
  local latest_name=""
  local saw_batch_dir=0

  shopt -s nullglob
  local dirs=("$dataset_root"/*/)
  shopt -u nullglob

  for dir in "${dirs[@]}"; do
    [[ -d "$dir" ]] || continue
    local base="${dir%/}"
    base="${base##*/}"

    if ! is_batch_name "$base"; then
      continue
    fi

    saw_batch_dir=1

    # Skip unreadable/unsearchable batch directories instead of selecting
    # them and then failing during summary.
    if [[ ! -r "$dir" || ! -x "$dir" ]]; then
      continue
    fi

    if [[ -z "$latest_name" || "$base" > "$latest_name" ]]; then
      latest_name="$base"
      latest_dir="${dir%/}"
    fi
  done

  if [[ -z "$latest_dir" ]]; then
    if [[ "$saw_batch_dir" -eq 1 ]]; then
      echo "No readable batch directories found under: $dataset_root" >&2
      return 2
    fi
    return 1
  fi

  printf '%s\n' "$latest_dir"
}

summarize_batch_dir() {
  local batch_dir="$1"
  local total_files
  local json_count

  total_files=$(find "$batch_dir" -type f | wc -l | tr -d ' ')
  json_count=$(find "$batch_dir" -maxdepth 1 -type f -name '*.json' | wc -l | tr -d ' ')

  printf 'Batch directory: %s\n' "$batch_dir"
  printf 'Total files: %s\n' "$total_files"
  printf 'Top-level JSON files: %s\n' "$json_count"

  if [[ "$json_count" -eq 0 ]]; then
    printf 'Metadata type counts: none\n'
    return 0
  fi

  printf 'Metadata type counts:\n'
  find "$batch_dir" -maxdepth 1 -type f -name '*.json' -print0 \
    | xargs -0 jq -r '
        (.metadata // {}) as $metadata
        | ($metadata | keys_unsorted) as $keys
        | if ($keys | length) == 0 then "none" else $keys[] end
      ' \
    | LC_ALL=C sort \
    | uniq -c \
    | while read -r count metadata_type; do
        printf '  %s: %s\n' "$metadata_type" "$count"
      done
}

resolve_batch_dir() {
  local target="$1"
  local batch_dir=""

  if [[ ! -d "$target" ]]; then
    echo "Directory does not exist: $target" >&2
    exit 2
  fi

  if is_batch_name "$target"; then
    batch_dir="$target"
  else
    if batch_dir="$(latest_batch_dir "$target")"; then
      :
    elif has_top_level_json "$target"; then
      batch_dir="$target"
    else
      echo "No batch directories found under: $target" >&2
      exit 2
    fi
  fi

  printf '%s\n' "$batch_dir"
}

if [[ $# -eq 0 ]]; then
  summarize_batch_dir "$(resolve_batch_dir "$(resolve_default_dataset_path)")"
  exit 0
fi

if [[ $# -eq 1 ]]; then
  summarize_batch_dir "$(resolve_batch_dir "$1")"
  exit 0
fi

arg_index=0
for target in "$@"; do
  arg_index=$((arg_index + 1))
  if [[ ! -d "$target" ]]; then
    echo "Directory does not exist: $target" >&2
    exit 2
  fi

  summarize_batch_dir "$target"
  if [[ "$arg_index" -lt "$#" ]]; then
    printf '\n'
  fi
done
