# pEyeON

EyeON is a CLI tool that allows users to get software data pertaining to their machines by performing threat and inventory analysis. It can be used to quickly generate manifests of installed software or potential firmare patches. These manifests are then submitted to a database and LLNL can use them to continuously monitor OT software for threats.

[![CI Test Status](https://github.com/LLNL/pEyeON/actions/workflows/unittest.yml/badge.svg)](https://github.com/LLNL/pEyeON/actions/workflows/unittest.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/LLNL/pEyeON/main.svg)]()
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/LLNL/pEyeON/blob/main/LICENSE)

<p align="center">
<img src="Photo/EyeON_Mascot.png" width="300" height="270">

## Motivation

Validation is important when installing new software. Existing tools use a hash/signature check to validate that the software has not been tampered. Knowing that the software works as intended saves a lot of time and energy, but just performing these hash/signature checks doesn't provide all the information needed to understand supply chain threats. 

EyeON provides an automated, consistent process across users to scan software files used for operational technologies. Its findings can be used to generate reports that track software patterns, shedding light on supply chain risks. This tool's main capabilities are focused on increasing the visibility of OT software landscape. 

## Installation
Eyeon can also be run in linux or WSL.

The simplest install can be done with `pip`:
```bash
pip install peyeon
```

However, this does not install several key dependencies, namely `libmagic`, `ssdeep`, and `tlsh`. A better way to install is via the container or install scripts on the github page.

### Containers
The container images include the main extraction dependencies such as `ssdeep`, `libmagic`, `tlsh`, and `detect-it-easy`.

#### Published Multi-Arch Image
The primary container image is published to GHCR as a multi-arch image. The same tag works on both `amd64` and `arm64` hosts, and Docker will pull the matching architecture automatically.

```bash
docker pull ghcr.io/llnl/peyeon:latest
docker run --rm ghcr.io/llnl/peyeon:latest eyeon --help
```

To test a development image without touching the released image, override the tag explicitly:

```bash
docker pull ghcr.io/llnl/peyeon-dev:dev
docker run --rm ghcr.io/llnl/peyeon-dev:dev eyeon --help
```

#### Local Docker Build
```bash
docker build -f builds/Dockerfile -t peyeon .
docker run --rm -it -v "$(pwd):/workdir:Z" peyeon /bin/bash
```

#### Local Podman Build
```bash
podman build -t peyeon -f builds/podman.Dockerfile .
podman run --rm -it -v "$(pwd):/workdir:rw" peyeon /bin/bash
```

These direct `docker run` and `podman run` examples are intended for interactive development shells and demos. The primary compute-oriented container workflow is `eyeon-parse.sh`, documented in its own section below.

### VM Install
Alternatively, to install on a clean Ubuntu or RHEL8/9 VM:

#### Ubuntu
Ubuntu installs are split into root and user steps. Run the system dependency install once, then run the user environment setup whenever you want to recreate or refresh the virtual environment from the current checkout.

```bash
sudo bash builds/install-ubuntu-root.sh
bash builds/install-ubuntu-user.sh
```

The compatibility wrapper `builds/install-ubuntu.sh` will run the root script when invoked with `sudo`, and the user script otherwise.

If you previously ran an older Ubuntu install flow entirely with `sudo`, you may need to clean up Surfactant's temp state once:

```bash
sudo rm -f /tmp/.surfactant_extracted_dirs.json
```

#### Ubuntu on Apple Silicon with Multipass
On an Apple Silicon Mac, a native Ubuntu VM can be created with Multipass:

```bash
multipass launch 24.04 --name eyeon-arm --cpus 4 --memory 8G --disk 40G
multipass mount ~/git/LLNL/pEyeON eyeon-arm:/workspace/pEyeON
multipass shell eyeon-arm
cd /workspace/pEyeON
sudo bash builds/install-ubuntu-root.sh
bash builds/install-ubuntu-user.sh
```

Verify the CLI inside the VM:

```bash
source eye/bin/activate
eyeon --help
```

#### RHEL8/9
```bash
wget https://raw.githubusercontent.com/LLNL/pEyeON/refs/heads/main/builds/install-rhel.sh
chmod +x install-rhel.sh && ./install-rhel.sh
```

To request other options for install, please create an issue on our GitHub page.


## Usage

This section shows how to run the CLI component. 

1. Displays all arguments 
```bash
eyeon --help
```

2. Displays observe arguments 
```bash
eyeon observe --help
```

3. Displays parse arguments 
```bash
eyeon parse --help
```

EyeON consists of two parts - an observe call and a parse call. `observe.py` works on a single file to return a suite of identifying metrics, whereas `parse.py` expects a folder. Both of these can be run either from a library import or a CLI command.

#### Observe

1. This CLI command calls the `observe` function and makes an observation of a file. 

CLI command:

```bash
eyeon observe demo.ipynb
```

Init file calls observe function in `observe.py`

```bash
obs = eyeon.observe.Observe("demo.ipynb")
```
The observation will create a json file containing unique identifying information such as hashes, modify date, certificate info, etc.

Example json file:

```json
{
    "bytecount": 9381, 
    "filename": "demo.ipynb", 
    "signatures": {"valid": "N/A"}, 
    "imphash": "N/A", 
    "magic": "JSON text data", 
    "modtime": "2023-11-03 20:21:20", 
    "observation_ts": "2024-01-17 09:16:48", 
    "permissions": "0o100644", 
    "md5": "34e11a35c91d57ac249ff1300055a816", 
    "sha1": "9388f99f2c05e6e36b279dc2453ebea4bdc83242", 
    "sha256": "fa95b3820d4ee30a635982bf9b02a467e738deaebd0db1ff6a262623d762f60d", 
    "ssdeep": "96:Ui7ooWT+sPmRBeco20zV32G0r/R4jUkv57nPBSujJfcMZC606/StUbm/lGMipUQy:U/pdratRqJ3ZHStx4UA+I1jS"
}
```

#### Parse
`parse.py` calls `observe` recursively, returning an observation for each file in a directory. 

```bash
obs = eyeon.parse.Parse(args.dir)
```

### eyeon-parse.sh
`eyeon-parse.sh` is the primary container wrapper for batch parsing. It treats the container as compute only:

- the source directory is mounted read-only at `/source`
- the dataset root is mounted read-write at `/workdir`
- parse output is written directly back to the host under the dataset root

The wrapper creates a timestamped output directory named `<timestamp>_<UTIL_CD>` under the dataset path and then runs `eyeon parse` inside the container.

#### Basic Usage
Option form:

```bash
./eyeon-parse.sh --util-cd UTIL_CD --dir SOURCE --dataset-path DATASET_PATH --threads 8
```

Positional form:

```bash
./eyeon-parse.sh UTIL_CD SOURCE [DATASET_PATH] [THREADS]
```

Examples:

```bash
./eyeon-parse.sh TESTSITE ./samples /data/eyeon
./eyeon-parse.sh TESTSITE ./samples /data/eyeon 16
./eyeon-parse.sh TESTSITE ./samples 16
```

`THREADS` defaults to `8`.

If `DATASET_PATH` is not provided, the wrapper uses `datasets.dataset_path` from `EyeOnData.toml`. If that is also unset, it falls back to `$HOME/data/eyeon`.

#### Latest Batch Summary
`eyeon-latest-batch-summary.sh` prints a short summary for the newest parse batch directory, including total file count, top-level JSON count, and counts by metadata type.

```bash
./eyeon-latest-batch-summary.sh
./eyeon-latest-batch-summary.sh /data/eyeon
./eyeon-latest-batch-summary.sh /data/eyeon/20260417T120000Z_TESTSITE
```

#### Container Image Selection
By default the wrapper uses the published production image:

```bash
ghcr.io/llnl/peyeon:latest
```

To test a dev image, override `EYEON_IMAGE`:

```bash
EYEON_IMAGE=ghcr.io/llnl/peyeon-dev:dev ./eyeon-parse.sh TESTSITE ./samples /data/eyeon
```

#### Runtime Selection
`eyeon-parse.sh` supports both Docker and Podman.

- set `EYEON_CONTAINER_RUNTIME=docker` or `EYEON_CONTAINER_RUNTIME=podman`
- or pass `--runtime docker` / `--runtime podman`
- if neither is set, the wrapper auto-selects the runtime only when exactly one of them is installed
- if both are installed, the wrapper stops and asks you to choose explicitly

Examples:

```bash
./eyeon-parse.sh --runtime docker TESTSITE ./samples /data/eyeon
./eyeon-parse.sh --runtime podman TESTSITE ./samples /data/eyeon
EYEON_CONTAINER_RUNTIME=podman ./eyeon-parse.sh TESTSITE ./samples /data/eyeon
```

For Podman, the wrapper relies on Podman's default runtime behavior instead of passing explicit UID/GID overrides.

#### Ownership Behavior
When run as a normal user, the wrapper passes your current UID and GID into the container so output files remain owned by you on the host.

When run as `root`, the wrapper requires you to choose the output owner explicitly unless you intentionally want root-owned output files.

Run as root but write files as a named user:

```bash
EYEON_OWNER=alice ./eyeon-parse.sh TESTSITE ./samples /data/eyeon
```

Run as root with explicit numeric ownership:

```bash
EYEON_UID=12345 EYEON_GID=12345 ./eyeon-parse.sh TESTSITE ./samples /data/eyeon
```

Intentionally allow root-owned outputs:

```bash
EYEON_PASSTHROUGH_ROOT=1 ./eyeon-parse.sh TESTSITE ./samples /data/eyeon
```

#### Runtime Matrix

| Runtime | Host mode | Wrapper behavior | In-container write identity | Resulting host file ownership |
| --- | --- | --- | --- | --- |
| Docker | Normal user | Passes caller UID/GID into container | `entrypoint.sh` remaps with `gosu` to caller UID/GID | Caller UID/GID |
| Docker | Root shell with `EYEON_OWNER` or `EYEON_UID`/`EYEON_GID` | Resolves target owner, `chown`s new output dir, passes target UID/GID | `entrypoint.sh` remaps with `gosu` to requested UID/GID | Requested UID/GID |
| Docker | Root shell with `EYEON_PASSTHROUGH_ROOT=1` | Passes root through intentionally | Root | Root |
| Podman | Normal user | Does not pass UID/GID overrides | Podman default rootless mapping | Caller UID/GID |
| Podman | Root shell | Root-run Podman path is not the primary tested mode | Runtime-dependent | Treat as admin/debug use only |

Notes:

- Docker uses explicit UID/GID handoff from the wrapper into the container.
- Podman currently works best by relying on Podman's default runtime behavior rather than forcing UID/GID overrides.
- In root-run Docker mode, the wrapper must know which non-root host owner should receive the output files.
- The wrapper creates the timestamped output directory on the host before launching the container. In root-run Docker mode it also `chown`s that directory to the requested target owner before execution.

#### Debug Mode
Set `DEBUG=1` or pass `--debug` to turn the wrapper into an interactive debugging session.

```bash
DEBUG=1 ./eyeon-parse.sh TESTSITE ./samples /data/eyeon
./eyeon-parse.sh --debug TESTSITE ./samples /data/eyeon
```

Debug mode does the following:

- prints the resolved wrapper environment values
- prints the full `docker run` command before launch
- passes `DEBUG=1` into the container
- prints entrypoint and runtime UID/GID information inside the container
- shows metadata for `/source`, `/workdir`, and `/tmp`
- opens an interactive `bash` shell instead of immediately running `eyeon parse`

Inside the debug shell, the intended parse command is written to `/tmp/eyeon-debug-command.sh` so it can be inspected or run directly:

```bash
cat /tmp/eyeon-debug-command.sh
/tmp/eyeon-debug-command.sh
```

#### Checksum Check

The Eyeon tool has the ability to verify against a provided sha1, md5, or sha256 hash. This can be leveraged as a stand alone function or with observe command to record the result in the output. If no algorithm is specified with `-a, --algorithm` it will default to md5.

```bash
eyeon checksum -a [md5,sha1,sha256] <file> <provided_checksum>
```

For convenience you can parse, compress, and upload your results to box in a single command:

```bash
eyeon parse <dir> --upload
```
To set up box and upload results, see **Uploading Results** section below


**Examples**
Stand Alone Check
```bash
eyeon checksum -a sha256 tests/binaries/Wintap.exe bdd73b73b50350a55e27f64f022db0f62dd28a0f1d123f3468d3f0958c5fcc39
```

Eyeon Observe
```bash
eyeon observe tests/binaries/Wintap.exe -a sha256 -c bdd73b73b50350a55e27f64f022db0f62dd28a0f1d123f3468d3f0958c5fcc39
```

Recorded Result in Eyeon Output
```json
    "checksum_data": {
        "algorithm": "sha256",
        "expected": "bdd73b73b50350a55e27f64f022db0f62dd28a0f1d123f3468d3f0958c5fcc39",
        "actual": "bdd73b73b50350a55e27f64f022db0f62dd28a0f1d123f3468d3f0958c5fcc39",
        "verified": true
    }
```

#### Jupyter Notebook
If you want to run jupyter from the container, launch the image with the notebook port exposed and a bind mount for your working directory:

```bash
docker run --rm -it -p 8888:8888 -v "$(pwd):/workdir:Z" ghcr.io/llnl/peyeon:latest /bin/bash
jupyter notebook --ip=0.0.0.0 --no-browser
```

Then open the `demo.ipynb` notebook for a quick demonstration.


#### Streamlit app
In the `src` directory, there exist the bones of a data exploration applet. To generate data for this, add the database flag like `eyeon parse -d tests/data/20240925-eyeon/dbhelpers/20240925-eyeon.db`. Then, if necessary, update the database path variable in the `src/streamlit/eyeon_settings.toml`. Note that the path needs to point to the grandparent directory of the `dbhelpers` directory. This is a specific path for the streamlit app; the streamlit directory has more information in its own README.

## Uploading Results
The Eyeon tool leverages the Box platform for data uploads and storage. All data handled by Eyeon is voluntarily submitted by users and securely stored in your Box account. If you wish to share the results of the eyeon tool with us please contact `eyeon@llnl.gov` to get setup.

#### Authenticating with Box
To use Eyeon with Box, you’ll need to generate a `box_tokens.json` file. This process requires a browser-friendly environment and will vary depending on your Eyeon build selection. Below are the steps when using a container setup:

**Steps**:

1. Create a Python virtual environment within the `PEYEON/` directory:
```bash
python -m venv .venv
source .venv/bin/activate
```
2. Install the Box SDK:
```bash
pip install boxsdk==3.14.0
```
3. Change into the `src/` directory:
```bash
cd src/
```
4. Start the authentication process:
```bash
python -m box.box_auth
```
This will guide you through authenticating with Box in your browser.

Once authentication is complete and your `box_tokens.json` file is generated, you can start the Eyeon Docker container and use the commands listed below.

#### List Items in Your Box Folder
```bash
eyeon box-list
```

Displays all items in your connected Box folder.

#### Upload Results to Box

```bash
eyeon box-upload <archive>
```

Uploads the specified archive (zip, tar, tar.gz) to your Box folder.


## Future Work
There will be a second part to this project, which will be to develop a cloud application that anonymizes and summarizes the findings to enable OT security analysis.

SPDX-License-Identifier: MIT
