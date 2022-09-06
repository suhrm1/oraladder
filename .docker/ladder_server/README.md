# OpenRA Ladder Game Server Dockerfile

This [Dockerfile](./Dockerfile) extends the base image created by [rmoriz](https://github.com/rmoriz/openra-dockerfile), `rmoriz/openra` on [Docker Hub](https://hub.docker.com/r/rmoriz/openra/).

Building this image updates operating system packages to current versions and adds a couple of utilities useful for running Ladder game servers:

- OpenRA lobby settings get pinned to the default competitive multiplayer values (see `_overrides` dictionary in [`srvwrap_minimal.py`](./srvwrap_minimal.py)).
- Banned OpenRA forum accounts are loaded from a file (which must contain one profile ID per line). The bans-file can be configured via the environment variable `BANS_FILE`. Default path is `/home/openra/banned_profiles`.
- Custom game server launch script [`server.sh`](./server.sh) rotates the starting map as a random pick from the available map folder.

## Usage

### Building the Docker Image

In this directory run `docker build`:

`docker build . -t oraladder/server:latest`

### Running the Game Server

Minimal command to run a game server is

`docker run -p 1234:1234 -e Mod=ra oraladder/server:latest`

In production settings, more sophisticated scaffolding is necessary to synchronise replay folders. The following example may serve as a base for such a setup:

```shell
RELEASE=release-20210321
docker run -dit \
    -p $PORT:$PORT \
    -e Name="Competitive 1v1 Ladder Server" \
    -e RequireAuthentication=True \
    -e EnableSingleplayer=False \
    -e RecordReplays=True \
    -e Mod=$MOD \
    -e ListenPort="$PORT" \
    -e TZ=UTC \
    -v ./replays/:/home/openra/.openra/Replays/$MOD/$RELEASE/:rw \
    -v ./maps/$MOD/:/home/openra/lib/openra/mods/$MOD/maps/:rw \
    -v ./banned_profiles:/home/openra/banned_profiles:ro \
    --add-host="resource.openra.net:127.0.0.99" \
    --restart always \
    --name openra_server \
    oraladder/server:latest
docker exec -it -u root openra_server sh -c "chown openra: -R /home/openra/.openra/"
```

Notably, `--add-host="resource.openra.net:127.0.0.99"` prevents the game server to download maps from the OpenRA Resource Center, effectively locking the map pool to what is locally available in the `maps` directory.

Mod can be switched between Red Alert and Tiberian Dawn by setting the environment variable `Mod=ra` or `Mod=cnc` (NB: not `td`!).