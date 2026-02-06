#!/usr/bin/env bash
set -euo pipefail

# Change these if you rename things
IMAGE="${IMAGE:-ghcr.io/autowarefoundation/autoware:universe-devel-cuda}"
WS_HOST="${WS_HOST:-$HOME/autoware_ws}"
MAP_HOST="${MAP_HOST:-$HOME/autoware_map}"

# Container paths
WS_CONT="/home/autoware/autoware_ws"
MAP_CONT="/home/autoware/autoware_map"

# Allow local docker containers to access X11 (safer than xhost +)
xhost +SI:localuser:root >/dev/null

# Pull image (optional but helpful)
docker pull "$IMAGE"

docker run --rm -it --runtime=nvidia --network host \
  -e DISPLAY="${DISPLAY:-:0}" \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$WS_HOST":"$WS_CONT":rw \
  -v "$MAP_HOST":"$MAP_CONT":rw \
  --workdir "$WS_CONT" \
  "$IMAGE" \
  bash

# Cleanup X access (optional)
xhost -SI:localuser:root >/dev/null
