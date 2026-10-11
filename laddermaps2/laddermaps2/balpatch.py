"""Download and extract balance patch archives from GitHub."""

import io
import os
import shutil
import zipfile
from urllib.request import urlopen

from laddermaps2.config import BALPATCH_URL, SRC_PREFIX


def download_balance_patch(tag, dest_dir, verbose=False):
    """Download the ora-balance-iteration archive and extract its ``src/``.

    Parameters
    ----------
    tag : str
        Git tag to fetch (e.g. ``"5.0"``).
    dest_dir : str
        Local directory to extract into.  If it already exists the
        download is skipped (cached).
    verbose : bool
        Print progress messages.

    Returns
    -------
    str
        Path to *dest_dir* containing the extracted ``.yaml`` rules.
    """
    if os.path.isdir(dest_dir):
        if verbose:
            print(f"  Using cached balance patch at {dest_dir}")
        return dest_dir

    url = BALPATCH_URL.format(tag=tag)
    if verbose:
        print(f"  Downloading {url}")

    resp = urlopen(url)
    data = resp.read()
    prefix = SRC_PREFIX.format(tag=tag)

    os.makedirs(dest_dir, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if name.startswith(prefix) and not name.endswith("/"):
                rel = os.path.relpath(name, prefix)
                target = os.path.join(dest_dir, rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    if verbose:
        files = os.listdir(dest_dir)
        print(f"  Extracted {len(files)} file(s) to {dest_dir}")
        for f in sorted(files):
            print(f"    {f}")

    return dest_dir


def read_extension_yaml(balpatch_dir):
    """Read ``_extension.yaml`` metadata from the patch directory.

    The extension YAML declares which files belong under which
    ``map.yaml`` category header (Rules, Weapons, …).

    Returns
    -------
    dict
        Mapping of category name → comma-separated filenames, or empty
        dict if the file doesn't exist.
    """
    import yaml

    ext_path = os.path.join(balpatch_dir, "_extension.yaml")
    if not os.path.exists(ext_path):
        return {}
    with open(ext_path) as f:
        return yaml.safe_load(f) or {}
