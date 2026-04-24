ARG LATEST_PYTHON_3_13=python:3.13-slim
FROM $LATEST_PYTHON_3_13 AS builder

RUN apt-get update \
    && apt-get install -y \
       git make wget unzip build-essential python3 python3-dev python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


RUN arch=$(dpkg --print-architecture) \
    && case "$arch" in \
        amd64) cmake_arch=x86_64 ;; \
        arm64) cmake_arch=aarch64 ;; \
        *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; \
    esac \
    && cmake_version=3.30.3 \
    && cmake_installer="cmake-${cmake_version}-linux-${cmake_arch}.sh" \
    && wget "https://github.com/Kitware/CMake/releases/download/v${cmake_version}/${cmake_installer}" \
    && chmod u+x "$cmake_installer" \
    && mkdir -p "/opt/cmake-${cmake_version}" \
    && "./$cmake_installer" --skip-license --prefix="/opt/cmake-${cmake_version}" \
    && rm "$cmake_installer" \
    && ln -sf /opt/cmake-${cmake_version}/bin/* /usr/local/bin

RUN cd /opt && git clone https://github.com/trendmicro/tlsh.git \
    && cd /opt/tlsh \
    && ./make.sh

COPY . /src
RUN python3 -m venv /eye \
    && /eye/bin/pip install --upgrade pip setuptools wheel \
    && /eye/bin/pip install /src

#################################################

FROM $LATEST_PYTHON_3_13
COPY --from=builder /opt/tlsh/bin /opt/tlsh/bin
COPY --from=builder /eye /eye

RUN apt-get update \
    && apt-get install -y \
      libmagic1 ssdeep jq gosu \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# look for entrypoint in basedir when pulling files
# or entrypoint from builds folder when cloning
COPY *entrypoint.sh *builds/*entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENV PATH="/eye/bin:$PATH"

# pull the plugin dbs, then remove Surfactant's root-owned temp state so the
# runtime user can recreate it as needed.
RUN surfactant plugin update-db --all \
    && rm -f /tmp/.surfactant_extracted_dirs.json

WORKDIR /workdir
ENTRYPOINT ["/entrypoint.sh"]
