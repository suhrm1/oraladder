#!/bin/bash
.docker/build.sh
docker tag oraladder/ragl:latest oraladder/ragl:s14-dev
docker save -o ~/Downloads/ragl.tar oraladder/ragl:s14-dev
rsync -P ~/Downloads/ragl.tar milkman@oraladder.net:~/
ssh milkman@oraladder.net "docker load -i ~/ragl.tar && cd /home/openra && docker-compose up -d"
