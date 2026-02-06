### 4utonomy Nav
## This repo contains:

docker/ Dockerfile and helper scripts to run Autoware in Docker
src/ Autoware workspace source packages and custom changes

#Large data like maps and bags are not stored in this repo.

##Folder layout on your machine
#Create these folders:

~/autoware_ws (this repo)
~/autoware_map (downloaded separately)
#After setup it should look like:

~/autoware_ws docker/ src/ .gitignore README.md

~/autoware_map (map files here)

##Prerequisites
Ubuntu 22.04
Docker installed
NVIDIA GPU + NVIDIA Container Toolkit (for --runtime=nvidia)
Enough disk space for Autoware build and maps
##Get the workspace
#Clone this repo:

git clone https://github.com/ASAS-Labs/4utonomy-Nav ~/autoware_ws

##Get the map (download from Google Drive)
Download the map archive from Google Drive:

Link:
Unzip it into:

~/autoware_map

##Start the autoware docker installation
Run it on terminal:

cd autoware_ws/Docker ./docker/run.sh

##Build the workspace inside the container
source /home/autoware/autoware_ws/install/setup.bash cd /home/autoware/autoware_ws colcon build --symlink-install source install/setup.bash

##Run Autoware with the map
ros2 launch autoware_launch planning_simulator.launch.xml map_path:=/home/autoware/autoware_map/uni_map2 vehicle_model:=sample_vehicle sensor_model:=sample_sensor_kit
