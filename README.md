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

### Dockerfile
This dockerfile contains all the pertinent tools specific to data extraction. The main tools needed are `ssdeep`, `libmagic`, `tlsh`, and `detect-it-easy`. We have written some convenient scripts for both docker and podman installations:

#### Docker
```bash
cd builds/
docker build -t peyeon -f Dockerfile .
chmod +x docker-run.sh && ./docker-run.sh
```
#### Podman
```bash
podman build -t peyeon -f builds/podman.Dockerfile .
chmod +x builds/podman-run.sh && ./builds/podman-run.sh
```

This attaches the current directory as a working directory in the container. Files that need to be scanned should go in "tests" folder. If running in a docker container, the eyeon root directory is mounted to `/workdir`, so place samples in `/workdir/samples` or `/workdir/tests/samples`.

Cd into workdir directory:
```bash
cd workdir
```

EyeON commands should work now.

### VM Install
Alternatively, to install on a clean Ubuntu or RHEL8/9 VM:
```bash
wget https://raw.githubusercontent.com/LLNL/pEyeON/refs/heads/main/builds/install-ubuntu.sh
chmod +x install-ubuntu.sh && ./install-ubuntu.sh
```

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
If you want to run jupyter, the `./docker-run.sh` script exposes port 8888. Launch it from the `/workdir` or eyeon root directory via `jupyter notebook --ip=0.0.0.0 --no-browser` and open the `demo.ipynb` notebook for a quick demonstration.


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
