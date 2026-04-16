#!/bin/bash

set -euo pipefail

TARGET_UID="${EYEON_UID:-}"
TARGET_GID="${EYEON_GID:-}"
DEBUG_MODE="${DEBUG:-0}"
TARGET_SOURCE="explicit-env"
REMOVED_SURFACTANT_STATE=0

# Prefer the caller's explicit UID/GID when provided. Fall back to the mounted
# workdir owner for older launchers that don't pass them through.
if [[ -z "$TARGET_UID" || -z "$TARGET_GID" ]]; then
    TARGET_UID=$(stat -c '%u' /workdir)
    TARGET_GID=$(stat -c '%g' /workdir)
    TARGET_SOURCE="workdir-owner"
fi

# Surfactant may leave a root-owned temp state file behind during image build.
# Remove it before dropping privileges so the runtime user can recreate it.
if [[ -e /tmp/.surfactant_extracted_dirs.json && ! -w /tmp/.surfactant_extracted_dirs.json ]]; then
    rm -f /tmp/.surfactant_extracted_dirs.json
    REMOVED_SURFACTANT_STATE=1
fi

if [[ "$DEBUG_MODE" == "1" && -n "${EYEON_DEBUG_COMMAND:-}" ]]; then
    cat > /tmp/eyeon-debug-command.sh <<EOF
#!/usr/bin/env bash
set -euo pipefail
${EYEON_DEBUG_COMMAND}
EOF
    chmod 755 /tmp/eyeon-debug-command.sh
    chown "$TARGET_UID:$TARGET_GID" /tmp/eyeon-debug-command.sh 2>/dev/null || true
fi

# Create group if it doesn't exist.
if ! getent group "$TARGET_GID" > /dev/null 2>&1; then
    groupadd -g "$TARGET_GID" eyeon
fi

# Create user if it doesn't exist.
if ! getent passwd "$TARGET_UID" > /dev/null 2>&1; then
    useradd -u "$TARGET_UID" -g "$TARGET_GID" -s /bin/bash -m eyeon
fi

if [[ "$DEBUG_MODE" == "1" ]]; then
    echo "DEBUG: entrypoint running as $(id -u):$(id -g)" >&2
    echo "DEBUG: target runtime uid/gid $TARGET_UID:$TARGET_GID ($TARGET_SOURCE)" >&2
    echo "DEBUG: removed stale surfactant temp state: $REMOVED_SURFACTANT_STATE" >&2
    gosu "$TARGET_UID:$TARGET_GID" /bin/bash -lc '
        echo "DEBUG: effective uid/gid $(id -u):$(id -g)" >&2
        echo "DEBUG: mounted paths" >&2
        ls -ld /source /workdir /tmp 2>/dev/null >&2 || true
        if [[ -x /tmp/eyeon-debug-command.sh ]]; then
            echo "DEBUG: intended parse command saved at /tmp/eyeon-debug-command.sh" >&2
            echo "DEBUG: intended parse command: ${EYEON_DEBUG_COMMAND}" >&2
        fi
    '
fi

exec gosu "$TARGET_UID:$TARGET_GID" "$@"
