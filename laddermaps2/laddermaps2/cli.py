"""CLI entry point for the ``laddermaps2`` command.

Parses arguments (with optional YAML config file override), then
runs the full pipeline: balance patch download → map resolution →
overlay generation → patching → optional ``--check-yaml``.
"""

import argparse
import os
import subprocess
import sys

from laddermaps2.balpatch import download_balance_patch
from laddermaps2.maps import resolve_maps
from laddermaps2.overlay import generate_overlay
from laddermaps2.patcher import process_maps


def _check_yaml_maps(ra_executable, output_dir):
    """Run OpenRA's ``--check-yaml`` on every ``.oramap`` in *output_dir*.

    Parameters
    ----------
    ra_executable : str
        Path to the OpenRA Red Alert executable.
    output_dir : str
        Directory containing patched ``.oramap`` files.
    """
    output_dir = os.path.abspath(output_dir)
    for fname in sorted(os.listdir(output_dir)):
        if not fname.endswith(".oramap"):
            continue
        path = os.path.join(output_dir, fname)
        print(f"\n  Checking: {fname}")
        result = subprocess.run(
            [ra_executable, "--utility", "--check-yaml", path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        for line in result.stdout.splitlines():
            print(f"    {line}")
        for line in result.stderr.splitlines():
            print(f"    {line}")


def parse_args(argv=None):
    """Build and return the argument parser namespace.

    Accepts an optional *argv* list for testability (defaults to
    ``sys.argv[1:]``).
    """
    parser = argparse.ArgumentParser(description="Build ladder map packs for OpenRA competitive ladder.")
    parser.add_argument("--season", help='Season tag, e.g. "2026.1"')
    parser.add_argument(
        "--bi-tag",
        dest="bi_tag",
        help='Balance iteration git tag, e.g. "5.0"',
    )
    parser.add_argument(
        "--map-ids",
        dest="map_ids",
        help="Comma-separated map IDs from resource.openra.net",
    )
    parser.add_argument(
        "--input-dir",
        dest="input_dir",
        help="Directory containing .oramap source files",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default="./output",
        help="Output directory for patched maps (default: ./output)",
    )
    parser.add_argument(
        "--balpatch-dir",
        dest="balpatch_dir",
        default="./.balpatch",
        help="Temp dir to store downloaded balance patch (default: ./.balpatch)",
    )
    parser.add_argument(
        "--cache-dir",
        dest="cache_dir",
        default="./.mapcache",
        help="Temp dir to cache downloaded maps (default: ./.mapcache)",
    )
    parser.add_argument(
        "--work-dir",
        dest="work_dir",
        default="./.work",
        help="Temp working directory for patching (default: ./.work)",
    )
    parser.add_argument(
        "--extensions-dir",
        dest="extensions_dir",
        default=None,
        help="Directory with extra extension YAML files (e.g. ERCC, briefing)",
    )
    parser.add_argument(
        "--ra-executable",
        dest="ra_executable",
        help="Path to OpenRA Red Alert executable for --check-yaml validation",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML config file with all settings",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args(argv)


def load_config(config_path):
    """Load a YAML config file.

    Parameters
    ----------
    config_path : str
        Path to the YAML file.

    Returns
    -------
    dict
        Parsed configuration.
    """
    import yaml

    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def merge_config(args, cfg):
    """Merge YAML config values into the parsed CLI args namespace.

    CLI-provided values take precedence over config file values.
    The ``maps`` section is expanded into ``map_ids`` / ``input_dir``.
    """
    d = vars(args)
    for k, v in cfg.items():
        yk = k.replace("-", "_")
        if yk in d and d[yk] is None:
            d[yk] = v
    if "maps" in cfg and isinstance(cfg["maps"], dict):
        mc = cfg["maps"]
        if "ids" in mc and d.get("map_ids") is None:
            d["map_ids"] = ",".join(str(i) for i in mc["ids"])
        if "input_dir" in mc and d.get("input_dir") is None:
            d["input_dir"] = mc["input_dir"]
    return argparse.Namespace(**d)


def main():
    """Entry point: parse, merge config, validate, run pipeline, exit."""
    args = parse_args()
    if args.config:
        cfg = load_config(args.config)
        args = merge_config(args, cfg)

    missing = []
    if not args.season:
        missing.append("--season")
    if not args.bi_tag:
        missing.append("--bi-tag")
    if not args.map_ids and not args.input_dir:
        missing.append("--map-ids or --input-dir")
    if missing:
        print("Error: missing required arguments: " + ", ".join(missing))
        print("Provide them via CLI or --config file.")
        sys.exit(1)

    if args.verbose:
        print(f"Season:     {args.season}")
        print(f"BI tag:     {args.bi_tag}")
        print(f"Map ids:    {args.map_ids or '(from input dir)'}")
        print(f"Input dir:  {args.input_dir or '(from IDs)'}")
        print(f"Output dir: {args.output_dir}")

    os.makedirs(args.output_dir, exist_ok=True)

    print("Downloading balance patch...")
    balpatch_dir = download_balance_patch(args.bi_tag, args.balpatch_dir, args.verbose)

    print("Resolving source maps...")
    source_maps = resolve_maps(args.map_ids, args.input_dir, args.cache_dir, args.verbose)

    print("Generating overlay...")
    overlay_svg, overlay_png = generate_overlay(args.season, args.verbose)

    if not args.extensions_dir:
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        default_ext = os.path.join(os.path.dirname(pkg_dir), "extensions")
        if os.path.isdir(default_ext):
            args.extensions_dir = default_ext

    print("Processing maps...")
    process_maps(
        source_maps,
        balpatch_dir,
        args.season,
        args.bi_tag,
        overlay_png,
        args.output_dir,
        args.work_dir,
        extensions_dir=args.extensions_dir,
        verbose=args.verbose,
    )

    print(f"\nDone! {len(source_maps)} maps written to {args.output_dir}")

    if args.ra_executable:
        print("\nChecking YAML with OpenRA utility...")
        _check_yaml_maps(args.ra_executable, args.output_dir)
