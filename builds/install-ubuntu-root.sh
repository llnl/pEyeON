#!/bin/bash

set -euo pipefail

arch=$(dpkg --print-architecture)

case "$arch" in
    amd64)
        cmake_arch=x86_64
        ;;
    arm64)
        cmake_arch=aarch64
        ;;
    *)
        echo "Unsupported architecture: $arch" >&2
        exit 1
        ;;
esac

apt-get update
DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC \
    apt-get install -y python3 python3-pip python3-dev python3-venv \
    libmagic1 git make wget unzip build-essential vim ssdeep jq \
    openjdk-17-jre-headless

# CMake is required to build telfhash and Ubuntu's packaged version may be too old.
cmake_version=3.30.3
cmake_root="/opt/cmake-${cmake_version}"

if [ ! -x "${cmake_root}/bin/cmake" ]; then
    cmake_installer="cmake-${cmake_version}-linux-${cmake_arch}.sh"
    tmpdir=$(mktemp -d)
    trap 'rm -rf "$tmpdir"' EXIT

    wget -O "${tmpdir}/${cmake_installer}" \
        "https://github.com/Kitware/CMake/releases/download/v${cmake_version}/${cmake_installer}"
    chmod u+x "${tmpdir}/${cmake_installer}"
    mkdir -p "$cmake_root"
    "${tmpdir}/${cmake_installer}" --skip-license --prefix="$cmake_root"
fi

ln -sf ${cmake_root}/bin/* /usr/local/bin

if [ ! -d /opt/tlsh/.git ]; then
    git clone https://github.com/trendmicro/tlsh.git /opt/tlsh
fi

cd /opt/tlsh
./make.sh

echo "Ubuntu system dependencies installed successfully on $arch"
