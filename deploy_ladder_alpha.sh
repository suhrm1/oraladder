#!/bin/bash
.docker/build.sh
docker tag oraladder/ladder:dev oraladder/ladder:3.0-alpha
docker save -o ~/Downloads/ladder.tar oraladder/ladder:3.0-alpha
rsync -P ~/Downloads/ladder.tar milkman@oraladder.net:~/
ssh milkman@oraladder.net "docker load -i ~/ladder.tar && cd /home/openra && docker-compose up -d"
