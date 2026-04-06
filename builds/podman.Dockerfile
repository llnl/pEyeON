ARG LATEST_PYTHON_3_13=python:3.13-slim
FROM $LATEST_PYTHON_3_13 AS builder

RUN apt-get update \
    && apt-get install -y \
       git make wget unzip build-essential python3 python3-dev python3-venv \
    && apt-get clean


RUN wget https://github.com/Kitware/CMake/releases/download/v3.30.3/cmake-3.30.3-linux-x86_64.sh \
    && chmod u+x cmake-3.30.3-linux-x86_64.sh \
    && mkdir /opt/cmake-3.30.3 \
    && ./cmake-3.30.3-linux-x86_64.sh --skip-license --prefix=/opt/cmake-3.30.3 \
    && rm cmake-3.30.3-linux-x86_64.sh \
    && ln -s /opt/cmake-3.30.3/bin/* /usr/local/bin

RUN cd /opt && git clone https://github.com/trendmicro/tlsh.git \
    && cd /opt/tlsh \
    && ./make.sh

RUN python3 -m venv /eye && /eye/bin/pip install peyeon

#################################################

FROM $LATEST_PYTHON_3_13
COPY --from=builder /opt/tlsh/bin /opt/tlsh/bin
COPY --from=builder /eye /eye

RUN apt-get update \
    && apt-get install -y \
      libmagic1 ssdeep jq gosu \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/eye/bin:$PATH"

# pull the plugin dbs
RUN surfactant plugin update-db --all

WORKDIR /workdir
