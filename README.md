# 4utonomy Nav

This repo contains:

- `docker/` Dockerfile and helper scripts to run Autoware in Docker
- `src/` Autoware workspace source packages and custom changes

Large data like maps and bags are not stored in this repo.

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
chmod +x docker/run.sh
./docker/run.sh
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

```
ros2 launch autoware_launch planning_simulator.launch.xml \
  map_path:=/home/autoware/autoware_map/uni_map2 \
  vehicle_model:=sample_vehicle \
  sensor_model:=sample_sensor_kit
```

