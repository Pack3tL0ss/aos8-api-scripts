# aos8-api-scripts

API Scripts for ArubaOS 8 Controller API

## How to prepare/use

Requires Python3, tested on Linux (tested specifically on wsl:ubuntu20.04, Linux Mint20, Windows 10)

- clone this repo to your system locally `git clone https://github.com/Pack3tL0ss/aos8-api-scripts.git`
- cd to aos8-api-scripts directory `cd aos8-api-scripts`

## Setting up the environment

### Linux:

> if pip3 is not recognized you may need to install it with `apt install python3-pip` (or the equivellent for your OS if not an apt based system)

```bash
pip3 install virtualenv
```

From within the cloned aos8-api-scripts directory:

```bash
python3 -m virtualenv venv
venv/bin/python3 -m pip install -r requirements.txt
```

#### Configuration files

*within the aos8-api-scripts directory*

```bash
cp config.yaml.example config.yaml
nano config.yaml
```

Then edit as required.
> The only IP/fqdns required are the Mobility Conductors, A complete list of Managed Devices is retrieved from the Conductors.

### Windows:

Requires Python3.x which can be installed from the Microsoft Store

*within the aos8-api-scripts directory*

```cmd
python3 -m pip install virtualenv
python3 -m virtualenv venv
venv\Scripts\activate
pip install -r requirements.txt
```

- copy config.yaml.example to config.yaml and edit for your environment


## Running Scripts

### Linux

venv/bin/python3 image_versions.py

### Windows

```cmd
venv\Scripts\activate
python3 image_versions.py
```

## OUTPUT

- results.csv: A csv with details for each Controller with columns for the image version in each partition among others
- results.txt: A report detailing what controller/partition contains each version found in the environment, along with a summary line indicating if any partitions were found with 6.x