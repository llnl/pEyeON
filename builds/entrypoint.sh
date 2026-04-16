#!/bin/bash

set -euo pipefail

TARGET_UID="${EYEON_UID:-}"
TARGET_GID="${EYEON_GID:-}"

# Prefer the caller's explicit UID/GID when provided. Fall back to the mounted
# workdir owner for older launchers that don't pass them through.
if [[ -z "$TARGET_UID" || -z "$TARGET_GID" ]]; then
    TARGET_UID=$(stat -c '%u' /workdir)
    TARGET_GID=$(stat -c '%g' /workdir)
fi

# Surfactant may leave a root-owned temp state file behind during image build.
# Remove it before dropping privileges so the runtime user can recreate it.
if [[ -e /tmp/.surfactant_extracted_dirs.json && ! -w /tmp/.surfactant_extracted_dirs.json ]]; then
    rm -f /tmp/.surfactant_extracted_dirs.json
fi

# Create group if it doesn't exist.
if ! getent group "$TARGET_GID" > /dev/null 2>&1; then
    groupadd -g "$TARGET_GID" eyeon
fi

# Create user if it doesn't exist.
if ! getent passwd "$TARGET_UID" > /dev/null 2>&1; then
    useradd -u "$TARGET_UID" -g "$TARGET_GID" -s /bin/bash -m eyeon
fi

exec gosu "$TARGET_UID:$TARGET_GID" "$@"
