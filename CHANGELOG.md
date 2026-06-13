# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security

## [3.0.1] - 2026-06-13

### Changed
- **Dependency upgrades — all packages bumped to latest:**
  - `black 23.1.0` → `26.5.1`
  - `Flask 2.2.2` → `3.1.3` (requires `werkzeug>=3.0.0`, pin removed)
  - `mariadb 1.1.9` → `1.1.14`
  - `numpy 1.24.1` → `2.4.6`
  - `openskill 4.0.0` → `6.2.0` (breaking API change — see Fixed)
  - `pre-commit 3.0.4` → `4.6.0`
  - `pydantic 1.10.4` → `2.13.4` (breaking API change — see Fixed)
  - `sqlalchemy 2.0.1` → `2.0.50`
  - `PyYAML 6.0` → `6.0.3`
  - `werkzeug <3.0.0` → `>=3.0.0`
- `setup.py`: added `python_requires>=3.10`, added `mariadb` dependency, moved dev-only packages to `extras_require["dev"]`
- `pyproject.toml`: Black `target-version` updated from `py39` to `py311`
- `.pre-commit-config.yaml`: black hook `22.10.0` → `26.5.1` (repo `ambv/black` → `psf/black`); pre-commit-hooks `v4.3.0` → `v5.0.0`
- `docker-compose.yml`: Ladder service now points to `.docker/Dockerfile_ladder` explicitly
- **README.md rewritten** for v3 project state (MariaDB, Docker Compose dev, admin UI, API); architecture, configuration, and project structure sections updated
- **Code comments and restructuring** added to all new files (`_flask_utils.py`, `admin.py`, `admin_dashboard.html`, `admin_replays.html`)
- Admin replay templates unified: single form action per tab, single modal with dynamic label

### Fixed
- **`flask.escape` removal:** Flask 3.0 removed the deprecated `escape` re-export; changed import to `markupsafe.escape`
- **openskill v6 API migration:** Top-level `openskill.Rating()`, `openskill.ordinal(r)`, and `openskill.rate()` removed in v6 — replaced with `PlackettLuce` model-based API (`model.rating()`, `r.ordinal()`, `model.rate(...)`)
- **pydantic v2 API migration:** `Season.dict()` → `Season.model_dump()`; callers updated in `api_system.py` and `database.py`
- **numpy v2 deprecation:** `numpy.testing.assert_almost_equal` → `numpy.testing.assert_allclose` in `test_glicko.py`
- **pre-commit hook tag:** Fixed `v5.0.1` → `v5.0.0` (nonexistent tag)

## [3.0.0] - 2026-06-13

### Added
- **MariaDB database backend:** Full migration from SQLite to MariaDB via `mariadb+mariadbconnector`. New `model/` package with standalone database abstraction layer (`database.py`), schema definitions (`_sql.py`), initialisation scripts (`init_mariadb.py`), and season model (`seasons.py`).
- **Docker Compose environment:** `docker-compose.yml` for local development — runs the ladder web app alongside a MariaDB container with health checks and persistent storage volumes.
- **Dockerfiles:** `Dockerfile` for building the ladder web app container; `.docker/Dockerfile_ladder` and `.docker/Dockerfile_base` for the deployment image.
- **System-admin REST API** (`api_system.py`): Protected by API key (`LADDER_API_KEY`), exposes `parse_replays`, `update_rankings`, `delete_replay`, `update_player_profiles`, `rotate_current_2m_season`, and related functions.
- **Admin UI** (`admin.py`): Blueprint-mounted at `/admin/` with HTTP BasicAuth and CSRF protection. Includes:
  - Dashboard with system status cards (game count, accounts, banned profiles), seasons overview, and configuration display
  - Action forms: Parse Replays, Update Rankings, Rotate Season, Update Player Profiles, Full System Refresh — all with prefilled defaults from server config
  - Replay management page with Active/Deleted tabs, multi-field filtering (mod, player, map, date range), multi-select delete (with password confirmation), and undelete support
- **Recommended replays page:** Spoiler-free replay recommendations using a new database view; separate page at `/recommended`
- **Individual replay page:** Dedicated `/replay/<hash>` endpoint returning the `.orarep` file as a download
- **Global statistics page:** `/stats` endpoint showing aggregate ladder metrics
- **Player profile enhancements:**
  - Opponent statistics table on player profile pages
  - Career statistics view (toggleable) as an alternative to season-specific stats
  - Player ranking history across seasons
- **Flask utility module** (`_flask_utils.py`): `create_app()` factory, `api_key_authn` decorator, `require_basicauth` decorator, and CSRF token generation/validation helpers
- **Announcements module** (`announcements.py`): infrastructure for site-wide notifications
- **Ranking criteria** (`ranking_criteria.py`): factorised game exclusion logic for rating calculations
- **YAML-based season configuration** (`seasons.yml`): multi-mod (RA, TD), multi-season (all-time, current 2-month) definitions via the season model in `model/seasons.py`
- **Map packs:** Added ladder map packs for OpenRA releases 2023.1, 2023.2, 2024.1, 2024.2, 2024.3, 2025.1, 2025.2 and TD map pack 2023.0
- **`ora-ladder`:** Added `openskill` algorithm based on the [OpenSkill module](https://github.com/OpenDebates/openskill.py). OpenRA ladder specific overrides prevent "negative" point assignment on loss and enforce a minimum point increase for every win.
- **`ora-dbtool`:** Added CLI arguments to auto-generate YAML metadata files for databases created
- **Game server Dockerfile:** `.docker/ladder_server/` with entrypoint, rotation script, and wrappers for running OpenRA dedicated servers

### Changed
- `ladderweb`:
  - **Model layer refactored:** All SQL schema definitions, data access, and season management moved from inline code in `__init__.py` into the standalone `model/` package. Supports both MariaDB and SQLite backends.
  - Season handling is now driven by `seasons.yml` instead of environment-variable-derived date ranges. Historic seasons are discovered dynamically from the database.
  - Player rank is now displayed in relation to total active players in the leaderboard and on `/player/` pages
  - `+/- 0` skill point changes shown in neutral styling instead of positive green
  - Replay listing page (`/replays`) added with filterable table of all replays
  - Navigation: added admin link removed from public nav (accessible at `/admin/` only)
  - Website header updated to reference current OpenRA release versions
  - All source files formatted with `black`
- `laddertools`:
  - Refactored ranking algorithm internals; algorithms are now loaded from the `rankings/` package
  - Updated replay processing and utility functions for compatibility with newer OpenRA formats
- Infrastructure: Dockerfiles updated for AppImage-based OpenRA builds; `pre-commit` config switched to Python 3.10

### Removed
- SQLite-only `seasons.py` module replaced by YAML-driven `model/seasons.py`
- Legacy `ranking.py` replaced by modular `rankings/` package
- Stale root-level `Dockerfile` removed in favor of organised `.docker/` directory

### Fixed
- Database initialisation race conditions on first startup
- Season loading for mods without active season data
- Debug output inadvertently enabled in production code paths
- Missing map pack files for earlier releases

### Security
- Admin UI protected by HTTP BasicAuth (`LADDER_ADMIN_USERNAME`/`LADDER_ADMIN_PASSWORD`) and per-form CSRF tokens
- Delete operations require password re-entry via modal
- Superfluous debug logging removed from production paths
- Werkzeug pinned to `<3.0` for compatibility

## [2.0.2] - 2022-11-20

### Added
- Added configuration files for development process tools `pre-commit` and `black`:
  - [`.pre-commit-config.yaml`](./.pre-commit-config.yaml) for [Pre-Commit](https://pre-commit.com/)
  - [`pyproject.toml`](./pyproject.toml) for [Black](https://black.readthedocs.io/en/stable/)
- Added `requirements.txt` file to pin Python module versions.

### Changed
- Re-formatted all source files using `black`

## [2.0.1] - 2022-11-10

### Added
- [Dockerfile](.docker/ladder_server/Dockerfile) for running OpenRA game servers; building on the base image by [rmoriz](https://github.com/rmoriz/openra-dockerfile) . This adds environment variable handling as well as a custom launch script for the game server that rotates starting maps.

## [2.0.0] - 2022-10-30

### Added
- Introduced changelog and bumped version to `2.0.0`. While this is not a release with any breaking changes, change in project organization and the number of changes since what was the initial production release merit a major release.
- Added `start` and `end` parameters to `ora-ladder` CLI to enable database file creation for specific timeframes
- Added CLI tool `ora-dbtool` to generate multiple 2-month-period database files in batch (basically a wrapper around the existing `ora-ladder` CLI)
- Added configuration parameters to control behaviour of `ladderweb` website, see subproject [README file](ladderweb/README.md).
- Added new `ladderweb` UI features:
  - Added CSS/JS based UI support for responsive navbar
  - Added exposition texts to `leaderboard` [template file](ladderweb/templates/leaderboard.html)
  - Added history of player rankings across seasons to `player` page
- Added ladder map pack [`2022.1`](ladderweb/static/ladder-map-pack-2021.1.zip); see corresponding maps on the
  [OpenRA resource center](https://resource.openra.net/maps/?mod=ra&category=Ladder+2022.1)

### Changed
- Refactored handling of database selection in the `ladderweb` subproject to allow for a dynamic number of 2-month-period databases
