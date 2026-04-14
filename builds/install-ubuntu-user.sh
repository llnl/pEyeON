#!/bin/bash

set -euo pipefail

if [ "$EUID" -eq 0 ]; then
    echo "Run this script as a normal user, not with sudo." >&2
    exit 1
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
eyeon_dir=$(cd -- "${script_dir}/.." && pwd)
surfactant_tmp_state=/tmp/.surfactant_extracted_dirs.json

if [ -e "$surfactant_tmp_state" ] && [ ! -w "$surfactant_tmp_state" ]; then
    echo "Surfactant temp state exists but is not writable: $surfactant_tmp_state" >&2
    echo "This is usually left behind by a previous sudo run." >&2
    echo "Remove it once with: sudo rm -f $surfactant_tmp_state" >&2
    exit 1
fi

cd "$eyeon_dir"
python3 -m venv eye
source eye/bin/activate
pip install --upgrade pip setuptools wheel
pip install .
surfactant plugin update-db --all

eyeon --help >/dev/null
echo "EyeON user environment installed successfully in $eyeon_dir/eye"
