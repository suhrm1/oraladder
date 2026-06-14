# ladderctl — OpenRA Dedicated Server Manager

A Flask web UI to manage OpenRA dedicated game servers via Docker. Start, stop, restart, remove and view logs of OpenRA server containers. Supports multiple mods (RA, CnC, D2k), named config presets, and on-demand image building from GitHub release AppImages.

## Project Structure

```
ladderctl/
├── app/                    # Python package
├── wsgi.py                 # Gunicorn entrypoint
├── templates/              # Jinja2 templates (index.html, logs.html)
├── server_config/          # Default config templates (banned_profiles, mappool, motd)
├── ladder_server/          # Docker build context for server images
├── Dockerfile              # ladderctl container image
├── docker-compose.yml      # Development compose file
└── requirements.txt
```

## Quickstart

### Prerequisites

- Docker Engine (with compose plugin)
- Git

### Development

```bash
git clone <repo> <project_root>
cd <project_root>/ladderctl

# Start the manager (listens on http://localhost:8001)
LADDERCTL_PASSWORD=secret docker compose up -d

# View logs
docker compose logs -f

# Restart after code changes
docker compose restart
```

The `docker-compose.yml` mounts `./ladder_server` read-only so Docker image builds from the host filesystem work without rebuilding the ladderctl container.

### Production

Set `LADDERCTL_BASEDIR` to a persistent host path for runtime artifacts (config files, replays, maps, `presets.json`).

```yaml
# docker-compose.yml override
services:
  ladderctl:
    environment:
      - LADDERCTL_BASEDIR=/var/lib/ladderctl
    volumes:
      - /var/lib/ladderctl:/var/lib/ladderctl
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

Default credentials: `admin` / `LADDERCTL_PASSWORD` (logs a generated one-time password if unset).

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LADDERCTL_USERNAME` | `admin` | HTTP BasicAuth user |
| `LADDERCTL_PASSWORD` | (auto-generated) | HTTP BasicAuth password |
| `LADDERCTL_BASEDIR` | `/tmp/oraladder-ladderctl` | Runtime data directory |
| `LADDERCTL_BASE_PORT` | `10300` | First host port allocated to game servers |
| `SECRET_KEY` | (auto-generated) | Flask session signing key |
| `DOCKER_HOST` | `unix:///var/run/docker.sock` | Docker daemon endpoint |

## Architecture Notes

- The container runs `docker-py` SDK calls and shells out to `docker build` via `subprocess` — it requires the Docker CLI binary inside the container for image building. The `python:3.11-slim` base image does not include the `docker` CLI; if image building is needed, install it in the Dockerfile or use a Docker-in-Docker sidecar.
- Server images are tagged `ladderctl/openra-server:<mod>-<release>` and built on demand from OpenRA GitHub release AppImages.
- Background tasks (image build + server launch) run as daemon threads — state is lost on crash.
- Config presets are persisted to `$LADDERCTL_BASEDIR/presets.json`.
