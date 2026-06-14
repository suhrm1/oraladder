import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from urllib.request import urlopen, Request

import docker
from flask import current_app

from .activity import add_activity

# ---------------------------------------------------------------------------
# Docker client
# ---------------------------------------------------------------------------


def docker_client():
    base_url = os.environ.get("DOCKER_HOST", "unix://var/run/docker.sock")
    return docker.DockerClient(base_url=base_url)


# ---------------------------------------------------------------------------
# Server listing
# ---------------------------------------------------------------------------

MANAGED_LABEL = "ladderctl.managed"


def _is_ladderctl_container(container):
    return (container.labels or {}).get(MANAGED_LABEL) == "1"


def is_ladderctl_container_name(name):
    """Check whether *name* refers to a ladderctl-managed container."""
    client = docker_client()
    try:
        c = client.containers.get(name)
        return _is_ladderctl_container(c)
    except docker.errors.NotFound:
        return False


def list_servers():
    """Return all containers (running + stopped) managed by ladderctl."""
    client = docker_client()
    return sorted(
        client.containers.list(all=True, filters={"label": f"{MANAGED_LABEL}=1"}),
        key=lambda c: c.name or c.id,
    )


def container_info(container):
    """Extract a summary dict from a Docker container object."""
    ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
    port_bindings = []
    for container_port, bindings in ports.items():
        if bindings:
            for b in bindings:
                port_bindings.append(f"{b.get('HostPort', '?')}->{container_port}")
        else:
            port_bindings.append(container_port)

    labels = container.labels or {}

    return {
        "id": container.short_id,
        "name": container.name,
        "status": container.status,
        "image": container.image.tags[0] if container.image.tags else str(container.image),
        "created": container.attrs.get("Created", ""),
        "ports": port_bindings,
        "mod": detect_mod(container),
        "labels": {k: v for k, v in labels.items() if k.startswith("ladderctl.")},
    }


def detect_mod(container):
    """Guess the mod from the container image tag or name.

    Tiberian Dawn is always ``cnc``; legacy ``td`` is normalised.
    """
    name = container.name or ""
    for tag in container.image.tags or []:
        for mod in ("ra", "cnc", "d2k"):
            if f"-{mod}" in tag or f"/{mod}-" in tag:
                return mod
        if "-td" in tag or "/td-" in tag:
            return "cnc"
    if "_cnc_" in name or "_td_" in name:
        return "cnc"
    if "_ra_" in name:
        return "ra"
    return "unknown"


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------


def get_config(key, default=""):
    return current_app.config.get(key, os.environ.get(key, default))


def get_basedir():
    """Return the host filesystem base directory for ladderctl artifacts.

    Respects the ``LADDERCTL_BASEDIR`` env var; falls back to a stable
    temporary directory under ``/tmp`` when not set.
    """
    override = os.environ.get("LADDERCTL_BASEDIR")
    if override:
        return override
    path = os.path.join(tempfile.gettempdir(), "oraladder-ladderctl")
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Server config management – file presets for banned_profiles, mappool, motd
# ---------------------------------------------------------------------------

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_server_config_dir = os.path.join(_project_root, "server_config")
_presets_path = os.path.join(get_basedir(), "presets.json")

CONFIG_FILE_KEYS = ("banned_profiles", "mappool_ra", "mappool_cnc", "motd.ra.txt", "motd.cnc.txt")
_KNOWN_MODS = frozenset({"ra", "cnc", "d2k"})


def get_default_config():
    """Read the default config files from ``server_config/``."""
    cfg = {}
    for key in CONFIG_FILE_KEYS:
        path = os.path.join(_server_config_dir, key)
        try:
            with open(path) as f:
                cfg[key] = f.read()
        except FileNotFoundError:
            cfg[key] = ""
    return cfg


def load_presets():
    """Return the list of saved named presets."""
    if not os.path.exists(_presets_path):
        return []
    try:
        with open(_presets_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_presets(presets):
    """Persist the preset list to disk."""
    with open(_presets_path, "w") as f:
        json.dump(presets, f, indent=2)


def write_config_files(basedir, mod, config):
    """Write per-mod and shared config files into *basedir* so Docker can
    bind-mount them as regular files."""
    if mod not in _KNOWN_MODS:
        raise ValueError(f"Invalid mod: {mod!r}")
    os.makedirs(basedir, exist_ok=True)

    files = {
        "banned_profiles": config.get("banned_profiles", ""),
        f"motd.{mod}.txt": config.get(f"motd.{mod}.txt", ""),
    }
    for filename, content in files.items():
        path = os.path.join(basedir, filename)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.islink(path) or os.path.isfile(path):
            os.unlink(path)
        with open(path, "w") as f:
            if filename.startswith("motd."):
                content = content.replace("\r", "")
            f.write(content)


# ---------------------------------------------------------------------------
# OpenRA release discovery (cached from GitHub API)
# ---------------------------------------------------------------------------

_releases_cache = {"timestamp": 0, "data": []}


def fetch_releases():
    """Return a list of OpenRA release tag names, newest first.

    Caches for 5 minutes. Falls back to a hardcoded list on failure.
    """
    now = time.time()
    if now - _releases_cache["timestamp"] < 300:
        return _releases_cache["data"]

    try:
        req = Request(
            "https://api.github.com/repos/OpenRA/OpenRA/releases?per_page=50",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "ladderctl"},
        )
        with urlopen(req, timeout=10) as resp:
            releases = json.loads(resp.read())
    except Exception as exc:
        current_app.logger.warning("Failed to fetch releases from GitHub: %s", exc)
        releases = _releases_cache["data"] or [{"tag_name": "release-20250330"}]

    result = []
    seen = set()
    for r in releases:
        tag = r.get("tag_name", "")
        if not (tag.startswith("release-") or tag.startswith("playtest-")):
            continue
        if tag in seen:
            continue
        seen.add(tag)
        date_str = tag[-8:]
        if date_str.isdigit() and int(date_str[:4]) < 2025:
            continue
        is_prerelease = "playtest" in tag or r.get("prerelease", False)
        result.append(
            {
                "tag": tag,
                "prerelease": is_prerelease,
                "published_at": r.get("published_at", ""),
            }
        )

    _releases_cache["data"] = result
    _releases_cache["timestamp"] = now
    return result


# ---------------------------------------------------------------------------
# OpenRA mod AppImage name mapping & release tag parsing
# ---------------------------------------------------------------------------

_MOD_APPIMAGE_MAP = {
    "ra": "Red-Alert",
    "cnc": "Tiberian-Dawn",
    "d2k": "Dune-2000",
}


def parse_release_tag(tag):
    """Split a tag like ``release-20250330`` or ``playtest-20260222``
    into ``(release_type, version_string)``."""
    for prefix in ("release-", "playtest-"):
        if tag.startswith(prefix):
            return prefix.rstrip("-"), tag[len(prefix) :]
    return "release", tag


# ---------------------------------------------------------------------------
# Docker image management – build on the fly if missing
# ---------------------------------------------------------------------------

BUILDER_IMAGE = "ladderctl/openra-server"
_RELEASE_RE = re.compile(r"^(release|playtest)-\d{8}$")


def ensure_image(release, mod="ra", log_func=print, force=False):
    """Make sure the server image exists locally; build if not.

    The Dockerfile in ``ladder_server/`` downloads the mod-specific OpenRA
    AppImage for *release* and *mod*, so each (mod, release) pair gets its
    own image tagged ``ladderctl/openra-server:<mod>-<release>``.

    *log_func* is called with status lines during the build so callers can
    stream progress to a task log or the console.

    When *force* is True any existing image with the same tag is removed
    before building.

    Returns the image tag string.
    """
    if not _RELEASE_RE.match(release):
        raise ValueError(f"Invalid release tag: {release!r}")

    tag = f"{BUILDER_IMAGE}:{mod}-{release}"
    client = docker_client()

    if force:
        try:
            client.images.remove(tag, force=True)
            log_func(f"Removed existing image {tag} for force-rebuild")
        except docker.errors.ImageNotFound:
            pass
    else:
        try:
            client.images.get(tag)
            log_func(f"Image {tag} already exists")
            return tag
        except docker.errors.ImageNotFound:
            pass

    openra_mod = _MOD_APPIMAGE_MAP.get(mod, "Red-Alert")
    release_type, version = parse_release_tag(release)

    log_func(f"Building {tag} ({openra_mod} AppImage) \u2026")
    current_app.logger.info("Building image %s (AppImage: %s, version: %s %s)", tag, openra_mod, release_type, version)
    dockerfile_dir = os.path.join(_project_root, "ladder_server")
    build_log = []

    def _stream_line(line):
        line = line.rstrip()
        if not line:
            return
        try:
            obj = json.loads(line)
            if "stream" in obj:
                text = obj["stream"].rstrip()
                if text:
                    build_log.append(text)
                    log_func(text)
                    current_app.logger.debug("build: %s", text)
        except json.JSONDecodeError:
            if line:
                build_log.append(line)
                log_func(line)

    proc = subprocess.Popen(
        [
            "docker",
            "build",
            "--tag",
            tag,
            "--build-arg",
            f"RELEASE_VERSION={version}",
            "--build-arg",
            f"RELEASE_TYPE={release_type}",
            "--build-arg",
            f"OPENRA_MOD={openra_mod}",
            "--rm",
            dockerfile_dir,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in proc.stdout:
        _stream_line(line)
    proc.wait()

    if proc.returncode != 0:
        err = proc.stderr.read() if proc.stderr else ""
        log_func(f"Build failed (exit {proc.returncode})")
        add_activity("Build failed", "\n".join(build_log[-20:]), "error")
        current_app.logger.error("Build failed for %s:\n%s", tag, err)
        raise RuntimeError(f"docker build exited {proc.returncode}: {err or build_log[-1][:200]}")
    add_activity("Build complete", "\n".join(build_log[-20:]), "success")
    current_app.logger.info("Built image %s", tag)
    return tag


# ---------------------------------------------------------------------------
# Map pool management – named collections of map UUIDs per mod
# ---------------------------------------------------------------------------

_map_pools_path = None


def _get_map_pools_path():
    global _map_pools_path
    if _map_pools_path is None:
        _map_pools_path = os.path.join(get_basedir(), "map_pools.json")
    return _map_pools_path


def load_map_pools():
    """Return the list of saved map pools."""
    path = _get_map_pools_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_map_pools(pools):
    """Persist the map pool list to disk as JSON."""
    path = _get_map_pools_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(pools, f, indent=2)


def fetch_map_info(uuid):
    """Fetch map metadata from the OpenRA Resource Center.

    Uses ``https://resource.openra.net/map/hash/<uuid>`` which returns
    a JSON array of map records.

    Returns a dict with keys (uuid, title, author, players, mod, categories)
    or *None* on failure.
    """
    url = f"https://resource.openra.net/map/hash/{uuid}"
    try:
        req = Request(url, headers={"User-Agent": "ladderctl"})
        with urlopen(req, timeout=10) as resp:
            records = json.loads(resp.read())
        if not isinstance(records, list) or not records:
            return None
        data = records[0]
        return {
            "uuid": data.get("map_hash", uuid),
            "title": data.get("title", ""),
            "author": data.get("author", ""),
            "players": int(data["players"]) if data.get("players") else 0,
            "mod": data.get("game_mod", "").lower(),
            "game_mod": data.get("game_mod", ""),
            "parser": data.get("parser", ""),
            "categories": data.get("categories", []),
        }
    except Exception as exc:
        current_app.logger.warning("Failed to fetch map info for %s: %s", uuid, exc)
        return None


def fetch_map_info_batch(uuids):
    """Fetch map metadata for multiple UUIDs in a single API call.

    Returns a dict mapping each UUID to its info dict (or an empty dict
    on failure).  The upstream endpoint accepts comma-separated UUIDs.
    """
    if not uuids:
        return {}
    url = f"https://resource.openra.net/map/hash/{','.join(uuids[:50])}"
    try:
        req = Request(url, headers={"User-Agent": "ladderctl"})
        with urlopen(req, timeout=15) as resp:
            records = json.loads(resp.read())
        if not isinstance(records, list):
            return {}
        result = {}
        for data in records:
            uid = data.get("map_hash", "")
            if uid:
                result[uid] = {
                    "uuid": uid,
                    "id": data.get("id"),
                    "title": data.get("title", ""),
                    "author": data.get("author", ""),
                    "uploader": data.get("uploader", ""),
                    "players": int(data["players"]) if data.get("players") else 0,
                    "width": data.get("width", ""),
                    "height": data.get("height", ""),
                    "tileset": data.get("tileset", ""),
                    "posted": data.get("posted", ""),
                    "mod": data.get("game_mod", "").lower(),
                    "parser": data.get("parser", ""),
                }
        return result
    except Exception as exc:
        current_app.logger.warning("Failed to fetch map info batch: %s", exc)
        return {}
