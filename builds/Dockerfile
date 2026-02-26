ARG LATEST_PYTHON_3_13=python:3.13-slim
FROM $LATEST_PYTHON_3_13 AS builder

RUN apt-get update \
    && apt-get install -y \
       git make wget unzip build-essential python3 python3-dev python3-venv \
       ca-certificates curl libmagic1 libmagic-dev \
       zlib1g-dev liblzma-dev liblzo2-dev libacl1-dev libzstd-dev liblz4-dev \
       android-sdk-libsparse-utils e2fsprogs p7zip-full unar \
       lzop lziprecover libhyperscan-dev zstd lz4 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/Kitware/CMake/releases/download/v3.30.3/cmake-3.30.3-linux-x86_64.sh \
    && chmod u+x cmake-3.30.3-linux-x86_64.sh \
    && mkdir /opt/cmake-3.30.3 \
    && ./cmake-3.30.3-linux-x86_64.sh --skip-license --prefix=/opt/cmake-3.30.3 \
    && rm cmake-3.30.3-linux-x86_64.sh \
    && ln -s /opt/cmake-3.30.3/bin/* /usr/local/bin

RUN cd /opt && git clone https://github.com/trendmicro/tlsh.git \
    && cd /opt/tlsh \
    && ./make.sh

RUN python3 -m venv /eye && /eye/bin/pip install peyeon \
    && /eye/bin/pip install --upgrade pip \
    && /eye/bin/pip install unblob

#Install sasquatch .deb (unblob dependency)
RUN curl -L -o /tmp/sasquatch_1.0.deb "https://github.com/onekey-sec/sasquatch/releases/download/sasquatch-v4.5.1-6/sasquatch_1.0_$(dpkg --print-architecture).deb" \
    && dpkg -i /tmp/sasquatch_1.0.deb \
    && rm /tmp/sasquatch_1.0.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#################################################

FROM $LATEST_PYTHON_3_13
COPY --from=builder /opt/tlsh/bin /opt/tlsh/bin
COPY --from=builder /eye /eye

RUN apt-get update \
    && apt-get install -y \
      libmagic1 ssdeep jq gosu \
      zlib1g liblzma5 liblzo2-2 libacl1 libzstd1 squashfs-tools e2fsprogs partclone \
      p7zip-full unar lzop lziprecover lz4 zstd android-sdk-libsparse-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#copy sasquatch binaries
COPY --from=builder /usr/bin/sasquatch /usr/bin/sasquatch
COPY --from=builder /usr/bin/sasquatch-v4be /usr/bin/sasquatch-v4be

# look for entrypoint in basedir when pulling files
# or entrypoint from builds folder when cloning
COPY *entrypoint.sh *builds/*entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENV PATH="/eye/bin:$PATH"

# pull the plugin dbs
RUN surfactant plugin update-db --all

WORKDIR /workdir
ENTRYPOINT ["/entrypoint.sh"]
