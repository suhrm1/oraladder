"""Resolve source maps from either resource.openra.net IDs or a local directory."""

import os
import shutil
from urllib.request import urlopen

from laddermaps2.config import MAP_URL


def resolve_maps(map_ids_str, input_dir, cache_dir, verbose=False):
    """Return a list of paths to ``.oramap`` files ready for patching.

    Parameters
    ----------
    map_ids_str : str or None
        Comma-separated numeric map IDs from resource.openra.net.
        Maps are downloaded into *cache_dir* unless already cached.
    input_dir : str or None
        Directory containing ``.oramap`` source files.  Ignored when
        *map_ids_str* is also given (both sources are merged).
    cache_dir : str
        Where to store downloaded maps (created if needed).
    verbose : bool
        Print progress messages.

    Returns
    -------
    list of str
        Absolute paths to ``.oramap`` files.

    Raises
    ------
    RuntimeError
        When no maps could be resolved from either source.
    """
    source_maps = []

    if map_ids_str:
        ids = [s.strip() for s in map_ids_str.split(",") if s.strip()]
        if verbose:
            print(f"  Will download {len(ids)} map(s) by ID")
        os.makedirs(cache_dir, exist_ok=True)
        for mid in ids:
            dest = os.path.join(cache_dir, f"{mid}.oramap")
            if not os.path.exists(dest):
                url = MAP_URL.format(map_id=mid)
                if verbose:
                    print(f"    Downloading {url}")
                resp = urlopen(url)
                with open(dest, "wb") as f:
                    shutil.copyfileobj(resp, f)
            source_maps.append(dest)

    if input_dir:
        if verbose:
            print(f"  Reading .oramap files from {input_dir}")
        for fname in sorted(os.listdir(input_dir)):
            if fname.lower().endswith(".oramap"):
                source_maps.append(os.path.join(input_dir, fname))

    if not source_maps:
        raise RuntimeError("No source maps found. Provide --map-ids or --input-dir.")

    if verbose:
        print(f"  Total source maps: {len(source_maps)}")
        for sm in source_maps:
            print(f"    {os.path.basename(sm)}")

    return source_maps
