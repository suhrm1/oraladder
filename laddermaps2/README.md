# laddermaps2

Build ladder map packs for the [oraladder.net](https://oraladder.net) OpenRA competitive ladder.

Two CLI tools are provided:

| Command | Description |
|---------|-------------|
| `laddermaps2` | Full build pipeline — download balance patch, patch maps, composite overlay |
| `upload-maps` | Upload finished `.oramap` packs to [resource.openra.net](https://resource.openra.net) |

---

## Install

```sh
pip install -e .
```

Requires Python ≥ 3.10.  System dependencies: a bold monospace font for the overlay
(e.g. `fonts-noto`, `fonts-dejavu-core`).

---

## Build pipeline — `laddermaps2`

### Quick start

```sh
# All options via CLI:
laddermaps2 --season 2026.1 --bi-tag 5.0 --map-ids 44149,25708,43246 --output-dir ./output

# From a local directory instead of IDs:
laddermaps2 --season 2026.1 --bi-tag 5.0 --input-dir ./source-maps --output-dir ./output

# Via YAML config file:
laddermaps2 --config config.yaml
```

### CLI options

| Option | Description |
|--------|-------------|
| `--season` | Season tag, e.g. `2026.1` **(required)** |
| `--bi-tag` | Balance iteration git tag, e.g. `5.0` **(required)** |
| `--map-ids` | Comma-separated numeric map IDs from resource.openra.net |
| `--input-dir` | Directory containing `.oramap` source files |
| `--output-dir` | Output directory for patched maps (default: `./output`) |
| `--balpatch-dir` | Temp directory for the downloaded balance patch (default: `./.balpatch`) |
| `--cache-dir` | Temp directory for cached map downloads (default: `./.mapcache`) |
| `--work-dir` | Temp working directory for unpacking/repacking (default: `./.work`) |
| `--extensions-dir` | Directory with extra YAML files to inject (default: `./extensions/` if it exists) |
| `--ra-executable` | Path to OpenRA Red Alert executable for `--check-yaml` validation after patching |
| `--config` | Path to YAML config file overriding CLI defaults |
| `--verbose` | Enable per-file progress messages |

At least one of `--map-ids` or `--input-dir` must be provided.  Both can be given at
once — results are merged.

### Config file reference

All CLI options can be provided via a YAML config file (see `config.yaml` for a
complete template):

```yaml
season: "2026.1"
bi_tag: "5.0"

maps:
  ids: [44149, 25708, 43246]
  # input_dir: ./source-maps

output_dir: ./output
balpatch_dir: ./.balpatch
cache_dir: ./.mapcache
work_dir: ./.work
extensions_dir: ./extensions
ra_executable: /path/to/OpenRA-Red-Alert.AppImage
```

CLI arguments take precedence over the config file.

### Pipeline steps

For each source map the tool performs these operations:

1. **Download balance patch** — fetches a `.zip` archive from
   `github.com/tttppp/ora-balance-iteration` at the given git tag and extracts the
   `src/` directory into `--balpatch-dir`.

2. **Resolve source maps** — downloads maps from `resource.openra.net` by ID (cached
   in `--cache-dir`), or reads local `.oramap` files from `--input-dir`.

3. **Generate overlay** — creates a 90×90 RGBA PNG (and equivalent SVG) with
   outlined white text ("Ladder" + season tag) using a bold monospace font.

4. **Unpack** — extracts the `.oramap` zip into a temporary directory.

5. **Strip old mod files** — removes recognised mod YAML files (bi-*, ragl-*,
   ercc*, bain2-*, briefing, lobby-rules, helper YAML, pink* files) and non-YAML
   assets (`.shp`, `.aud` files).  See `patcher.py`:`_is_mod_file()` for the
   full list.

6. **Clean junk** — removes `.DS_Store`, `Thumbs.db`, `desktop.ini`.

7. **Edit `map.yaml`**:
   - Strips references to removed files from all category lines (Rules, Weapons, …)
   - Sets `Title: {sanitised} [Ladder]` (removes any existing `[Ladder]` or `[BI-*]` tags)
   - Sets `Categories: Ladder-{season}, BI-{bi_tag}, Ladder, 1v1, Conquest`
   - Merges balance patch file references from `_extension.yaml`
   - Merges extension files (ERCC, briefing) into their respective category lines

8. **Add balance patch files** — copies all `.yaml` files from `--balpatch-dir` into
   the map (excluding forbidden files like `bi-briefing-rules.yaml`).

9. **Add extension files** — copies files from `--extensions-dir`.  The
   `ladder-briefing-rules.yaml` file gets its BI version string patched.

10. **Composite overlay** — resizes the overlay PNG to match the map's minimap
    dimensions and alpha-composites it onto `map.png`.

11. **Re-zip** — re-packs with `ZIP_DEFLATED` into `{title}_ladder_{season}.oramap`
    in `--output-dir`.

12. **Optional validation** — if `--ra-executable` is given, runs
    `OpenRA --utility --check-yaml` on every output file.

### Known mod files stripped from source maps

The patcher recognises and removes these categories of files from source maps
before injecting new rules:

- **bi-\*.yaml** — balance iteration files
- **ragl-\*.yaml** — RAGL-specific rules
- **ercc\*.yaml** — ERCC mod rules
- **bain2-\*.yaml** — BAIN2 mod rules
- **briefing.yaml**, **briefing-rules.yaml**, **ladder-briefing.yaml**
- **lobby-rules.yaml**
- **hlpr_\*** — helper YAML files
- **pink\*** — pink colour mod files
- **\*.shp** — custom shp assets (gpssactiveicon, pip-skull, tox_sign)
- **satellite_\*.aud** — satellite sound effects

Source maps must preserve `map.yaml`, `map.png`, and `map.bin`.

### Forbidden files

These files are never copied into output maps even if present in the balance
patch or extensions:

- `bi-briefing-rules.yaml`
- `bi-lobby-rules.yaml`

### Extension file directory (`extensions/`)

Files placed in this directory are injected into every map.  Currently includes:

| File | Category | Purpose |
|------|----------|---------|
| `ERCC2-sequences.yaml` | Sequences | ERCC mod animation sequences |
| `ERCC21andBCC11-rules.yaml` | Rules | ERCC mod rules |
| `ladder-briefing-rules.yaml` | Rules | Ladder briefing overlay (BI version auto-patched) |
| `ref-*.shp`, `harv-flipped_top.shp` | — | Custom shp assets |

### Output filenames

Output files are named `{slug}_ladder_{season}.oramap` where the slug is derived
from the map title: non-alphanumeric characters become underscores, then
lowercased.  Example: `arctic_paradise_ladder_2026.1.oramap`.

---

## Upload maps — `upload-maps`

After building map packs, upload the resulting `.oramap` files.

### Usage

```sh
# Interactive — prompts for anything not provided
upload-maps ./output/*.oramap

# Non-interactive (e.g. in a script)
upload-maps --username myuser --no-interactive ./output/*.oramap

# All options via CLI
upload-maps \
  --username myuser \
  --parser release-20250303 \
  --info "Ladder season 2026.1" \
  --policy-cc cc_yes \
  --commercial com_yes \
  --adaptations adapt_yes \
  ./output/*.oramap
```

### Interactive mode

When run without `--no-interactive`, the tool prompts for each value with the
previous session's entries pre-filled as defaults.  The password is always
prompted fresh — never stored.

Defaults are persisted in `~/.config/openra-uploader/config.json`.

### CLI options

| Option | Description |
|--------|-------------|
| `--username` | OpenRA Resource Center username |
| `--parser` | Parser version (default: `playtest-20260222`) |
| `--info` | Map description / info text |
| `--policy-cc` | Creative Commons license (`cc_yes` / `cc_no`) |
| `--commercial` | Allow commercial use (`com_yes` / `com_no`) |
| `--adaptations` | Allow adaptations (`adapt_yes` / `adapt_no` / `adapt_shared`) |
| `--config` | Path to JSON config file |
| `--no-interactive` | Fail if required params are missing instead of prompting |

### How it works

1. Logs in to `resource.openra.net` via session-based auth (Django CSRF handled
   automatically).
2. For each file, POSTs a multipart form to `/upload/map/` with the `.oramap`
   data, parser version, info text, and license policy.
3. On success, prints the numeric map ID assigned by the resource center.
4. Refreshes the CSRF token between uploads.

---

## Project structure

```
laddermaps2/
├── laddermaps2/
│   ├── __init__.py       # Package docstring, subcommand reference
│   ├── __main__.py       # python -m laddermaps2 entry point
│   ├── cli.py            # CLI arg parsing, config merging, pipeline orchestration
│   ├── config.py         # External resource URL constants
│   ├── balpatch.py       # Download & extract balance patch from GitHub
│   ├── maps.py           # Resolve source maps (download by ID / read local dir)
│   ├── overlay.py        # Generate "Ladder" season overlay (PNG + SVG)
│   ├── patcher.py        # Core patching pipeline (unpack, strip, merge, repack)
│   └── upload_maps.py    # Upload finished maps to resource.openra.net
├── extensions/           # Extra files injected into every map
│   ├── ERCC2-sequences.yaml
│   ├── ERCC21andBCC11-rules.yaml
│   ├── harv-flipped_top.shp
│   ├── ladder-briefing-rules.yaml
│   ├── ref-anim.shp
│   ├── ref-bot.shp
│   └── ref-top.shp
├── config.yaml           # Template YAML config file
├── pyproject.toml        # Package metadata, deps, console scripts
├── requirements.txt      # pip dependencies
├── overlay.svg           # Generated overlay (created at runtime)
├── overlay.png           # Generated overlay (created at runtime)
├── output/               # Default output directory (gitignored)
├── .balpatch/            # Temp balance patch cache (gitignored)
├── .mapcache/            # Temp map download cache (gitignored)
└── .work/                # Temp work directory (gitignored)
```
