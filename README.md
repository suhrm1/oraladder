# OpenRA Competitive Ladder

This repository contains all the sources used by the OpenRA community
competitive 1v1 ladder hosted on [oraladder.net](https://oraladder.net).

It contains:

- the web frontend written in Flask (Python)
- the backend tools (`ora-ladder`, `ora-replay`, `ora-dbtool`)
- the game server configuration and Dockerfiles
- optional subprojects for tournament websites (RAGL, RATL, TDGL)
- detailed explanations on the setup

For some context and history on the project, you can also read the following
blog post: [Building a competitive ladder for OpenRA][blog-post].

The project was overhauled in v3.0.0 (MariaDB backend, admin UI, REST API,
multi-mod support). The legacy v2 documentation is archived at
[`README.v2.md`](README.v2.md).

[blog-post]: http://blog.pkh.me/p/28-building-a-competitive-ladder-for-openra.html


## Architecture

The general architecture used on oraladder.net is pretty simple:

![Architecture](misc/architecture.png)

Game server instances are configured to record replays. On a regular basis,
the backend parses them to find the outcomes, identify the players, and update
their rankings. During ranking, the backend queries the OpenRA user accounts
API (external) to resolve player identities and obtain display names and avatar
URLs. The web frontend displays the results.

Each brick can technically be separated. Game servers can run on other
machines, replay files can be synchronised for the backend to read, and the
website can be hosted independently. Since replays contain all match
information, additional statistics and analysis can be added later.


## Quick start (development)

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (for the MariaDB database)

### Bootstrap

Create a virtualenv and install the project:

```sh
make
```

Start the MariaDB database:

```sh
docker compose up -d database
```

Start the development server:

```sh
make ladderdev
```

The site is accessible at http://127.0.0.1:5000 and changes in the source are
reflected immediately.

### Database

The application uses **MariaDB** as its database backend
(connection string configured via `FLASK_LADDER_MAIN_DATABASE`). On first
startup the required tables and views are created automatically.

The admin UI provides a dashboard at `/admin/` (BasicAuth; defaults:
`admin`/`admin`) with action forms to parse replays, update rankings, rotate
seasons, and refresh player profiles.

### Configuration

All configuration is done via environment variables with the `FLASK_LADDER_`
prefix:

| Variable | Description | Default |
|---|---|---|
| `FLASK_LADDER_MAIN_DATABASE` | MariaDB connection string | `mariadb+mariadbconnector://...` |
| `FLASK_LADDER_API_KEY` | API key for REST endpoints | auto-generated (printed on startup) |
| `FLASK_LADDER_ADMIN_USERNAME` | Admin UI username | `admin` |
| `FLASK_LADDER_ADMIN_PASSWORD` | Admin UI password | auto-generated (printed on startup) |
| `FLASK_LADDER_RA_DEFAULT_REPLAY_FOLDER` | Default RA replay directory | — |
| `FLASK_LADDER_TD_DEFAULT_REPLAY_FOLDER` | Default TD replay directory | — |
| `FLASK_LADDER_DELETED_REPLAY_FOLDER` | Archive for deleted replays | — |
| `FLASK_LADDER_BANS_FILE` | Path to banned profiles file | — |
| `SECRET_KEY` | Flask session signing key | auto-generated |

Season definitions are configured in [`ladderweb/seasons.yml`](ladderweb/seasons.yml).
Each entry defines a mod (`ra`, `td`), an algorithm (`openskill`, `elo`, etc.),
a duration, and a replay path.

### Admin UI

The admin UI is available at `/admin/` and provides:

- **Dashboard** — system status (games, accounts, banned profiles), seasons
  overview, configuration values
- **Parse Replays** — scan a directory for new `.orarep` files and ingest them
- **Update Rankings** — recalculate ratings, rankings, and highscores for one or
  all seasons
- **Rotate Season** — close the current 2-month season and open a fresh one
- **Update Player Profiles** — refresh names and avatar URLs from the OpenRA
  Forum API
- **Full System Refresh** — run the complete pipeline (parse → rank → rotate)
  for every configured mod
- **Manage Replays** — browse active and deleted replays with filtering by mod,
  player, map, and date range; multi-select delete (with password confirmation)
  and undelete

### REST API

System administration endpoints are also available via HTTP (protected by
`LADDER_API_KEY`):

| Endpoint | Method | Description |
|---|---|---|
| `/api/system/refresh` | POST | Full system refresh |
| `/api/system/update_rankings` | POST | Recalculate rankings |
| `/api/system/update_player_profiles` | POST | Refresh player profiles |
| `/api/rotate_current_season` | POST | Rotate current 2m season |
| `/api/<mod_id>/parse_replays` | POST | Parse replays for a mod |
| `/api/<mod_id>/<season_id>/update` | POST | Update a specific season |
| `/api/games/<hash>` | DELETE | Delete a specific replay |

The key can be passed as JSON body field `api_key`, query string parameter
`api_key`, or form field `api_key`.


## Production

### Docker (recommended)

A Docker Compose file is provided in the project root:

```sh
docker compose up -d
```

This starts the ladder web app (on port 8000) with a MariaDB database. The
ladder image can also be built standalone:

```sh
docker build -f .docker/Dockerfile_ladder -t oraladder/ladder .
```

See [`.docker/README.md`](.docker/README.md) for more details on images and
manual container setup.

### Manual setup

The old SQLite-based workflow (backup scripts, cron-based database refreshes,
`ora-ladder` CLI) is documented in [`README.v2.md`](README.v2.md) and remains
available for legacy deployments.


## CLI tools

The following command-line tools are included:

- **`ora-ladder`** — parse replay directories into database files (rating
  calculations, season management)
- **`ora-replay`** — inspect and analyse individual replay files
- **`ora-dbtool`** — batch-create 2-month-period database files with YAML
  metadata output
- **`ora-srvwrap`** — bootstrap and run OpenRA game server instances with
  competitive settings and map pool management
- **`ora-mapstool`** — download and pack map pools from the OpenRA Resource
  Center


## Game servers

The game server instances are configured to record replays. A dedicated
Dockerfile and utility scripts are available in [`.docker/ladder_server/`](.docker/ladder_server/README.md)
for running game servers with automatic map rotation and environment variable
configuration.

For manual game server setup, `ora-srvwrap` handles:

1. fetching and building OpenRA sources at the specified version
2. creating isolated game server instances
3. patching the mod with competitive settings
4. downloading maps from the map pool
5. running the server on a configurable port

See the [game server documentation](.docker/ladder_server/README.md) for
details on running multiple instances with map rotation.


## Project structure

```
├── ladderweb/          Flask web application (routes, templates, API, admin UI)
├── laddertools/        CLI tools (ora-ladder, ora-replay, ora-srvwrap) + ranking algorithms
├── .docker/            Dockerfiles for base image, ladder web app, and game server
├── misc/               Map pools, nginx config, architecture diagram
├── ladderweb/static/   CSS, JavaScript, map pack archives
├── ladderweb/model/    Database layer, schema definitions, season model
├── ladderweb/templates/Jinja2 templates (including admin/)
├── docker-compose.yml  MariaDB + ladder development environment
├── Makefile            Build and development targets
├── requirements.txt    Python dependencies
└── CHANGELOG.md        Release history
```


## Development

- **`make`** — create virtualenv and install dependencies
- **`make ladderdev`** — run the development server (requires `docker compose up -d database` first)
- **`make test`** — run tests
- **`make wheel`** — build a distributable Python wheel
- **`make mappacks`** — download and pack tournament map pools

The codebase is formatted with [Black](https://black.readthedocs.io/).
Pre-commit hooks are configured in `.pre-commit-config.yaml`.
