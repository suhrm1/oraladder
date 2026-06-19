# laddermaps2

Build ladder map packs for [oraladder.net](https://oraladder.net).

## Install

```sh
pip install -e .
```

## Usage

```sh
# All options via CLI:
laddermaps2 --season 2026.1 --bi-tag 5.0 --map-ids 44149,25708,43246 --output-dir ./output

# Or from a local directory:
laddermaps2 --season 2026.1 --bi-tag 5.0 --input-dir ./source-maps --output-dir ./output

# Or via config file:
laddermaps2 --config config.yaml
```

### CLI options

| Option | Description |
|---|---|
| `--season` | Season tag, e.g. `2026.1` (required) |
| `--bi-tag` | Balance iteration git tag, e.g. `5.0` (required) |
| `--map-ids` | Comma-separated map IDs from resource.openra.net |
| `--input-dir` | Directory containing `.oramap` source files |
| `--output-dir` | Output directory for patched maps (default: `./output`) |
| `--balpatch-dir` | Temp dir to store downloaded balance patch (default: `./.balpatch`) |
| `--cache-dir` | Temp dir to cache downloaded maps (default: `./.mapcache`) |
| `--work-dir` | Temp working directory for patching (default: `./.work`) |
| `--extensions-dir` | Directory with extra extension YAML files (e.g. ERCC, briefing) |
| `--ra-executable` | Path to OpenRA Red Alert executable for `--check-yaml` validation after patching |
| `--config` | Path to YAML config file with all settings |
| `--verbose` | Enable verbose output |

## What it does

1. Downloads a balance patch from `github.com/tttppp/ora-balance-iteration` by git tag
2. Fetches maps from `resource.openra.net` by ID (or reads local `.oramap` files)
3. Unpacks each map, strips old mod files, injects the balance patch + extension files (ERCC, briefing, etc.)
4. Updates `map.yaml` — merges refs, sets title to `[Ladder]`, sets categories
5. Composites an overlay (season tag) onto `map.png`
6. Re-packs into `{title}_ladder_{season}.oramap`

## Config file

All CLI options can be provided via YAML config instead:

```yaml
season: "2026.1"
bi_tag: "5.0"
maps:
  ids: [44149, 25708, 43246]
  # input_dir: ./source-maps
output_dir: ./output
# ra_executable: /path/to/OpenRA-Red-Alert.AppImage
```

See `config.yaml` for a full template.

## Project structure

```
laddermaps2/
├── laddermaps2/
│   ├── cli.py        # CLI + config file parsing
│   ├── patcher.py    # Core patching pipeline
│   ├── balpatch.py   # Download balance patch from GitHub
│   ├── maps.py       # Resolve source maps
│   └── overlay.py    # Generate overlay PNG
├── extensions/       # Extra files added to every map (ERCC, briefing)
├── config.yaml       # Template config file
└── pyproject.toml    # Package metadata
```
