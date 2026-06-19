"""Core map patching pipeline.

Takes source ``.oramap`` files, strips old mod YAML, injects balance
patch rules and extension files, updates ``map.yaml`` metadata,
composites a "Ladder" overlay onto the minimap, and re-packs into
the output directory.
"""

import os
import re
import shutil
import tempfile
import zipfile

from PIL import Image

from laddermaps2.balpatch import read_extension_yaml

#: Recognised mod YAML files that are stripped from source maps.
KNOWN_MOD_YAMLS = {
    "bi-balance-rules.yaml",
    "bi-briefing-rules.yaml",
    "bi-lobby-rules.yaml",
    "bi-player-rules.yaml",
    "bi-notifications.yaml",
    "bi-sequences.yaml",
    "bi-voices.yaml",
    "bi-weapons.yaml",
    "bi.ftl",
    "ragl-rules.yaml",
    "ragl-balance.yaml",
    "ragl-briefing.yaml",
    "ragl-briefing-rules.yaml",
    "ragl-balance-rules.yaml",
    "ragl-actor-rules.yaml",
    "ragl-actor-sequences.yaml",
    "ERCC2-rules.yaml",
    "ERCC21andBCC-rules.yaml",
    "ERCC2-sequences.yaml",
    "ercc2-rules.yaml",
    "ercc2-sequences.yaml",
    "bain2-rules.yaml",
    "bain2-weapons.yaml",
    "briefing.yaml",
    "briefing-rules.yaml",
    "lobby-rules.yaml",
    "ladder-briefing.yaml",
}

#: Non-YAML mod assets that are stripped from source maps.
KNOWN_NON_YAML_MODS = {}

#: ``map.yaml`` category headers that reference external files.
CATEGORY_LINES = [
    "Rules:",
    "Weapons:",
    "Sequences:",
    "Notifications:",
    "Voices:",
    "FluentMessages:",
]

#: Categories injected into every map's ``Categories:`` line.
EXTRA_CATEGORIES = ["Ladder", "1v1", "Conquest"]

#: Files that must never be copied into the output (e.g. source-only).
FORBIDDEN_FILES = {"bi-briefing-rules.yaml", "bi-lobby-rules.yaml"}

#: Map from extension filename to the ``map.yaml`` category it belongs under.
EXTENSIONS_CATEGORIES = {
    "ERCC21andBCC11-rules.yaml": "Rules",
    "ladder-briefing-rules.yaml": "Rules",
    "ERCC2-sequences.yaml": "Sequences",
}


def _is_mod_file(name):
    """Return True if *name* is a known mod file that should be stripped."""
    base = os.path.basename(name)
    if base in KNOWN_MOD_YAMLS:
        return True
    if base in KNOWN_NON_YAML_MODS:
        return True
    if re.match(r"^bi-.+\.yaml$", base, re.IGNORECASE):
        return True
    if re.match(r"^ragl-.+\.yaml$", base, re.IGNORECASE):
        return True
    if re.match(r"^ercc.+\.yaml$", base, re.IGNORECASE):
        return True
    if re.match(r"^bain2-.+\.yaml$", base, re.IGNORECASE):
        return True
    if re.match(r"^satellite_.+\.aud$", base, re.IGNORECASE):
        return True
    return False


def _sanitize_title(title):
    """Remove existing ``[Ladder]`` and ``[BI-…]`` tags from a map title."""
    title = title.strip()
    title = re.sub(r"\s*\[Ladder\]\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\[BI-[^\]]*\]\s*", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _to_filename(title, season):
    """Convert a map title into a slug-style filename with season suffix."""
    name = re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_").lower()
    return f"{name}_ladder_{season}.oramap"


def _read_lines(work_dir):
    """Read ``map.yaml`` as a list of lines."""
    path = os.path.join(work_dir, "map.yaml")
    with open(path, encoding="utf-8") as f:
        return f.readlines()


def _write_lines(work_dir, lines):
    """Write a list of lines back to ``map.yaml``."""
    path = os.path.join(work_dir, "map.yaml")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _find_header_line(lines, prefix):
    """Return ``(index, line)`` of the first line starting with *prefix*."""
    for i, line in enumerate(lines):
        if line.strip().startswith(prefix):
            return i, line
    return None, None


def _remove_file_refs(value, removed_files):
    """Drop filenames in *removed_files* from a comma-separated list."""
    parts = [p.strip() for p in value.split(",")]
    kept = [p for p in parts if p not in removed_files]
    return ", ".join(kept)


def _add_file_refs(value, files_to_add):
    """Append filenames not already present in a comma-separated list."""
    parts = [p.strip() for p in value.split(",")] if value else []
    for f in files_to_add:
        if f not in parts:
            parts.append(f.strip())
    return ", ".join(parts)


def _patch_briefing_version(content, bi_tag):
    """Replace ``BI X.Y`` version references in briefing content."""
    return re.sub(r"\bBI\s+[\d.]+\b", f"BI {bi_tag}", content)


def process_maps(
    source_maps, balpatch_dir, season, bi_tag, overlay_png, output_dir, work_dir, extensions_dir=None, verbose=False
):
    """Run the full patching pipeline on every source map.

    For each source ``.oramap``:

    1. Unpack into a temp directory.
    2. Remove old mod YAML and assets (see ``_is_mod_file``).
    3. Remove junk files (``.DS_Store``, etc.).
    4. Edit ``map.yaml`` — strip removed file refs, set title to
       ``{sanitised} [Ladder]``, set categories.
    5. Add balance patch files and register them in ``map.yaml``.
    6. Add extension files (e.g. briefing), patching BI version in
       ``ladder-briefing-rules.yaml``.
    7. Composite the "Ladder" overlay onto ``map.png``.
    8. Determine the output filename from the new title.
    9. Re-zip and write to *output_dir*.

    Parameters
    ----------
    source_maps : list of str
        Paths to input ``.oramap`` files.
    balpatch_dir : str
        Directory with extracted balance patch files.
    season : str
        Season tag (e.g. ``"2026.1"``), used in filename + categories.
    bi_tag : str
        Balance iteration tag (e.g. ``"5.0"``).
    overlay_png : str
        Path to the overlay PNG to composite.
    output_dir : str
        Where to write the patched ``.oramap`` files.
    work_dir : str
        Temporary working directory for unpacking / re-packing.
    extensions_dir : str or None
        Optional directory with extra YAML files to inject.
    verbose : bool
        Print per-map progress messages.
    """
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    ext = read_extension_yaml(balpatch_dir)
    balpatch_files = [f for f in os.listdir(balpatch_dir) if f != "_extension.yaml"]

    ext_files = {}
    if extensions_dir and os.path.isdir(extensions_dir):
        for fname in os.listdir(extensions_dir):
            fpath = os.path.join(extensions_dir, fname)
            if os.path.isfile(fpath):
                ext_files[fname] = fpath

    for sm_path in source_maps:
        basename = os.path.basename(sm_path)
        if verbose:
            print(f"\n  Processing: {basename}")

        with tempfile.TemporaryDirectory(dir=work_dir) as tmp:
            os.makedirs(tmp, exist_ok=True)

            # 1. Unpack
            with zipfile.ZipFile(sm_path) as zf:
                zf.extractall(tmp)

            # 2. Remove old mod files (YAML only + specific non-YAML)
            removed = set()
            for fname in list(os.listdir(tmp)):
                if fname in ("map.yaml", "map.png", "map.bin"):
                    continue
                if _is_mod_file(fname):
                    os.remove(os.path.join(tmp, fname))
                    removed.add(fname)
                    if verbose:
                        print(f"    Removed: {fname}")

            # 3. Remove junk files
            for fname in list(os.listdir(tmp)):
                if fname in (".DS_Store", "Thumbs.db", "desktop.ini"):
                    os.remove(os.path.join(tmp, fname))

            # 4. Edit map.yaml
            lines = _read_lines(tmp)
            new_lines = []
            for line in lines:
                stripped = line.strip()

                matched_prefix = None
                for prefix in CATEGORY_LINES:
                    if stripped.startswith(prefix):
                        matched_prefix = prefix
                        break

                if matched_prefix:
                    _, value = stripped.split(":", 1)
                    value = _remove_file_refs(value, removed)
                    indent = line[: len(line) - len(line.lstrip())]
                    new_lines.append(f"{indent}{matched_prefix} {value}\n")
                    continue

                if stripped.startswith("Title:"):
                    _, val = stripped.split(":", 1)
                    title = _sanitize_title(val)
                    indent = line[: len(line) - len(line.lstrip())]
                    new_lines.append(f"{indent}Title: {title} [Ladder]\n")
                    continue

                if stripped.startswith("Categories:"):
                    cats = [f"Ladder-{season}", f"BI-{bi_tag}"] + EXTRA_CATEGORIES
                    indent = line[: len(line) - len(line.lstrip())]
                    new_lines.append(f"{indent}Categories: {', '.join(cats)}\n")
                    continue

                new_lines.append(line)

            # Merge balance patch references from _extension.yaml
            for prefix in CATEGORY_LINES:
                key = prefix.rstrip(":")
                if key in ext:
                    files_to_add = [f.strip() for f in ext[key].split(",") if f.strip() not in FORBIDDEN_FILES]
                    idx, existing = _find_header_line(new_lines, prefix)
                    if idx is not None:
                        _, value = existing.strip().split(":", 1)
                        new_val = _add_file_refs(value, files_to_add)
                        indent = new_lines[idx][: len(new_lines[idx]) - len(new_lines[idx].lstrip())]
                        new_lines[idx] = f"{indent}{prefix} {new_val}\n"
                    else:
                        new_lines.insert(1, f"{prefix} {', '.join(files_to_add)}\n")

            # Merge extension files into map.yaml
            for fname, cat in EXTENSIONS_CATEGORIES.items():
                if fname not in ext_files:
                    continue
                prefix = f"{cat}:"
                idx, existing = _find_header_line(new_lines, prefix)
                if idx is not None:
                    _, value = existing.strip().split(":", 1)
                    new_val = _add_file_refs(value, [fname])
                    indent = new_lines[idx][: len(new_lines[idx]) - len(new_lines[idx].lstrip())]
                    new_lines[idx] = f"{indent}{prefix} {new_val}\n"
                else:
                    new_lines.insert(1, f"{prefix} {fname}\n")

            _write_lines(tmp, new_lines)

            # 5. Add balance patch files
            for key, val in ext.items():
                for fname in val.split(","):
                    fname = fname.strip()
                    if fname in FORBIDDEN_FILES:
                        continue
                    src = os.path.join(balpatch_dir, fname)
                    dst = os.path.join(tmp, fname)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        if verbose:
                            print(f"    Added: {fname}")

            for fname in balpatch_files:
                if fname in FORBIDDEN_FILES:
                    continue
                src = os.path.join(balpatch_dir, fname)
                dst = os.path.join(tmp, fname)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    if verbose:
                        print(f"    Added (extra): {fname}")

            # 6. Add extension files, patching BI version in briefing
            for fname, fpath in ext_files.items():
                dst = os.path.join(tmp, fname)
                if fname == "ladder-briefing-rules.yaml":
                    with open(fpath, "r", newline="") as f:
                        content = f.read()
                    content = content.replace("\r", "")
                    content = _patch_briefing_version(content, bi_tag)
                    with open(dst, "w", newline="") as f:
                        f.write(content)
                    if verbose:
                        print(f"    Added (ext, version {bi_tag}): {fname}")
                else:
                    shutil.copy2(fpath, dst)
                    if verbose:
                        print(f"    Added (ext): {fname}")

            # 7. Superimpose overlay on map.png
            map_png_path = os.path.join(tmp, "map.png")
            if os.path.exists(map_png_path):
                map_img = Image.open(map_png_path).convert("RGBA")
                overlay_img = Image.open(overlay_png).convert("RGBA")
                overlay_resized = overlay_img.resize(map_img.size, Image.LANCZOS)
                composited = Image.alpha_composite(map_img, overlay_resized)
                composited.save(map_png_path)
                if verbose:
                    print(f"    Overlay composited ({map_img.size[0]}x{map_img.size[1]})")

            # 8. Determine title for output filename
            lines = _read_lines(tmp)
            map_title = basename.replace(".oramap", "")
            for line in lines:
                if line.strip().startswith("Title:"):
                    _, val = line.strip().split(":", 1)
                    map_title = _sanitize_title(val)
                    break

            out_name = _to_filename(map_title, season)
            out_path = os.path.join(output_dir, out_name)

            # 9. Re-zip
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname in sorted(os.listdir(tmp)):
                    fpath = os.path.join(tmp, fname)
                    zf.write(fpath, fname)

            if verbose:
                print(f"    Written: {out_name}")
