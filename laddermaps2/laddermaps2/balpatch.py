import io
import os
import shutil
import zipfile
from urllib.request import urlopen

from laddermaps2.config import BALPATCH_URL, SRC_PREFIX


def download_balance_patch(tag, dest_dir, verbose=False):
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
    import yaml

    ext_path = os.path.join(balpatch_dir, "_extension.yaml")
    if not os.path.exists(ext_path):
        return {}
    with open(ext_path) as f:
        return yaml.safe_load(f) or {}
