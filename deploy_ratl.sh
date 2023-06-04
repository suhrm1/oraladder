#!/bin/bash
.docker/build.sh
docker tag oraladder/ratl:dev oraladder/ratl:s02-dev
docker save -o ~/Downloads/ratl.tar oraladder/ratl:s02-dev
rsync -P ~/Downloads/ratl.tar milkman@oraladder.net:~/
ssh milkman@oraladder.net "docker load -i ~/ratl.tar && cd /home/openra && docker-compose up -d"
