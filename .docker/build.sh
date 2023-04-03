#!/bin/sh
#
# Build OpenRA Ladder Docker images
#
# NB: run from project root directory (not within ".docker" directory)

#
# 0. prepare Dockerfile
#
cp .docker/Dockerfile* .

#
# 1. Build base image
#
docker build -t oraladder/base:latest -f Dockerfile_base .

#
# 2. Build RAGL image
#
#docker build -t oraladder/ragl:latest -f Dockerfile_ragl .

#
# 3. Build TDGL image
#
#docker build -t oraladder/tdgl:latest -f Dockerfile_tdgl .

#
# 4. Build OpenRA ladder image
#
docker build -t oraladder/ladder:dev -f Dockerfile_ladder .

#
# Cleanup
#
rm Dockerfile*
