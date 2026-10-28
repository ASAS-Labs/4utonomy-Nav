# 4utonomy Nav

> **4utonomy by ASAS Labs** - Production autonomous vehicle navigation system (2026)  
> This is a current production implementation by ASAS Labs, distinct from the historical "buggy" proposal.

This repo contains:

- `docker/` Dockerfile and helper scripts to run Autoware in Docker
- `src/` Autoware workspace source packages and custom changes
- `src/operational_risk_assessment/` Real-time operational risk assessment system

Large data like maps and bags are not stored in this repo.

## 🆕 New: Operational Risk Assessment System

A comprehensive real-time risk monitoring system for autonomous operations that monitors weather conditions, sensor health, and operational domain compliance. See [OPERATIONAL_RISK_ASSESSMENT.md](OPERATIONAL_RISK_ASSESSMENT.md) for complete documentation.

---

## Folder layout on your machine

Create these folders:

- `~/autoware_ws` (this repo)
- `~/autoware_map` (downloaded separately)

After setup it should look like:

~/autoware_ws/
docker/
src/
.gitignore
README.md

~/autoware_map/
(map files here)


---

## Prerequisites

- Ubuntu 22.04
- Docker installed
- NVIDIA GPU + NVIDIA Container Toolkit (for `--runtime=nvidia`)
- Enough disk space for Autoware build and maps

---

## Get the workspace

Clone this repo:

```bash
git clone https://github.com/ASAS-Labs/4utonomy-Nav.git ~/autoware_ws
```

## Get the map (download from Google Drive)

Download the map archive from Google Drive:

Link: 

Unzip it into:
```bash
mkdir -p ~/autoware_map
# unzip the downloaded file into ~/autoware_map
```

## Start the Autoware Docker container

### From your host terminal:

```bash
cd ~/autoware_ws
chmod +x docker/run_autoware.sh
./docker/run_autoware.sh
```

This will open a bash shell inside the container with these mounts:

~/autoware_ws -> /home/autoware/autoware_ws

~/autoware_map -> /home/autoware/autoware_map

## Build the workspace inside the container

### Inside the container:
```bash
cd /home/autoware/autoware_ws
colcon build --symlink-install
source install/setup.bash
```

If you open a new shell later, source again:
```
source /home/autoware/autoware_ws/install/setup.bash
```

## Run Autoware with the map

### Inside the container (after sourcing the workspace):

```bash
ros2 launch autoware_launch planning_simulator.launch.xml \
  map_path:=/home/autoware/autoware_map/uni_map2 \
  vehicle_model:=sample_vehicle \
  sensor_model:=sample_sensor_kit
```

## Operational Risk Assessment (Optional)

Launch the risk assessment system in a separate terminal:

```bash
# Inside the container
ros2 launch operational_risk_assessment risk_assessment.launch.py
```

Monitor the risk assessment:

```bash
ros2 topic echo /risk_assessment/overall
```

For complete documentation, see [OPERATIONAL_RISK_ASSESSMENT.md](OPERATIONAL_RISK_ASSESSMENT.md).

