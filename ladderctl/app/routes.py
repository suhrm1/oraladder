import os
import re

import docker
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app

from .auth import require_basicauth
from .helpers import (
    docker_client,
    list_servers,
    container_info,
    get_config,
    get_basedir,
    get_default_config,
    is_ladderctl_container_name,
    load_presets,
    save_presets,
    load_map_pools,
    save_map_pools,
    fetch_map_info,
    fetch_map_info_batch,
    write_config_files,
    CONFIG_FILE_KEYS,
    ensure_image,
    fetch_releases,
)
from . import tasks
from .activity import add_activity, get_activity

KNOWN_MODS = frozenset({"ra", "cnc", "d2k"})
_RELEASE_RE = re.compile(r"^(release|playtest)-\d{8}$")

bp = Blueprint("ladderctl", __name__)


@bp.route("/")
@require_basicauth
def index():
    servers = list_servers()
    stats = {
        "total": len(servers),
        "running": sum(1 for s in servers if s.status == "running"),
    }
    return render_template(
        "index.html",
        servers=[container_info(s) for s in servers],
        stats=stats,
        releases=fetch_releases(),
        activity=get_activity(),
        defaults=get_default_config(),
        presets=load_presets(),
        map_pools=load_map_pools(),
        tasks=tasks.all_tasks(),
    )


@bp.route("/api/servers")
@require_basicauth
def api_servers():
    servers = list_servers()
    return jsonify(
        {
            "stats": {
                "total": len(servers),
                "running": sum(1 for s in servers if s.status == "running"),
            },
            "servers": [container_info(s) for s in servers],
        }
    )


@bp.route("/api/releases")
@require_basicauth
def api_releases():
    return jsonify(fetch_releases())


@bp.route("/api/activity")
@require_basicauth
def api_activity():
    return jsonify(get_activity())


@bp.route("/api/server-config/defaults")
@require_basicauth
def api_config_defaults():
    return jsonify(get_default_config())


@bp.route("/api/server-config/presets")
@require_basicauth
def api_config_presets():
    return jsonify(load_presets())


@bp.route("/api/server-config/presets", methods=["POST"])
@require_basicauth
def api_config_presets_save():
    data = request.get_json(silent=True)
    if not data or not data.get("name"):
        return jsonify({"error": "Missing preset name"}), 400
    name = data["name"]
    presets = load_presets()
    entry = {"name": name}
    for key in CONFIG_FILE_KEYS:
        if key in data:
            entry[key] = data[key]
    for i, p in enumerate(presets):
        if p["name"] == name:
            presets[i] = entry
            break
    else:
        presets.append(entry)
    save_presets(presets)
    return jsonify(entry), 201


@bp.route("/api/server-config/presets/<name>", methods=["DELETE"])
@require_basicauth
def api_config_presets_delete(name):
    presets = load_presets()
    presets[:] = [p for p in presets if p["name"] != name]
    save_presets(presets)
    return "", 204


# ---------------------------------------------------------------------------
# Map pool API
# ---------------------------------------------------------------------------


@bp.route("/api/map-pools")
@require_basicauth
def api_map_pools():
    return jsonify(load_map_pools())


@bp.route("/api/map-pools", methods=["POST"])
@require_basicauth
def api_map_pools_save():
    data = request.get_json(silent=True)
    if not data or not data.get("name") or not data.get("mod"):
        return jsonify({"error": "Missing pool name or mod"}), 400
    name = data["name"]
    mod = data["mod"]
    release = data.get("release", "")
    if mod not in KNOWN_MODS:
        return jsonify({"error": f"Invalid mod: {mod}"}), 400
    if release and not _RELEASE_RE.match(release):
        return jsonify({"error": f"Invalid release: {release}"}), 400
    pools = load_map_pools()
    for p in pools:
        if p["name"] == name:
            p["mod"] = mod
            p["release"] = release
            p["maps"] = data.get("maps", p.get("maps", []))
            break
    else:
        pools.append({"name": name, "mod": mod, "release": release, "maps": data.get("maps", [])})
    save_map_pools(pools)
    return jsonify({"name": name, "mod": mod, "release": release}), 201


@bp.route("/api/map-pools/<name>", methods=["DELETE"])
@require_basicauth
def api_map_pools_delete(name):
    pools = load_map_pools()
    pools[:] = [p for p in pools if p["name"] != name]
    save_map_pools(pools)
    return "", 204


@bp.route("/api/map-pools/<name>/maps", methods=["POST"])
@require_basicauth
def api_map_pools_add_map(name):
    data = request.get_json(silent=True)
    if not data or not data.get("uuid"):
        return jsonify({"error": "Missing map UUID"}), 400
    uuid = data["uuid"].strip().lower()
    pools = load_map_pools()
    for p in pools:
        if p["name"] == name:
            if uuid not in p["maps"]:
                p["maps"].append(uuid)
            save_map_pools(pools)
            return jsonify({"uuid": uuid}), 201
    return jsonify({"error": "Pool not found"}), 404


@bp.route("/api/map-pools/<name>/maps/<uuid>", methods=["DELETE"])
@require_basicauth
def api_map_pools_remove_map(name, uuid):
    uuid = uuid.strip().lower()
    pools = load_map_pools()
    for p in pools:
        if p["name"] == name:
            p["maps"] = [m for m in p["maps"] if m != uuid]
            save_map_pools(pools)
            return "", 204
    return jsonify({"error": "Pool not found"}), 404


@bp.route("/api/map-info/<uuid>")
@require_basicauth
def api_map_info(uuid):
    info = fetch_map_info(uuid)
    if info is None:
        return jsonify({"error": "Map not found or API error"}), 404

    pool_mod = request.args.get("mod", "").lower().strip()
    pool_release = request.args.get("release", "").strip()

    result = {
        "uuid": info["uuid"],
        "title": info["title"],
        "author": info["author"],
        "players": info["players"],
        "mod": info["mod"],
        "categories": info["categories"],
    }

    if pool_mod:
        result["match_mod"] = info["mod"] == pool_mod.lower()
    if pool_release and info.get("parser"):
        result["match_release"] = info["parser"] == pool_release
        result["parser"] = info["parser"]

    return jsonify(result)


@bp.route("/api/map-info", methods=["POST"])
@require_basicauth
def api_map_info_batch():
    data = request.get_json(silent=True) or {}
    uuids = data.get("uuids", [])
    if not uuids:
        return jsonify({}), 200
    uuids = uuids[:50]
    result = fetch_map_info_batch(uuids)
    return jsonify(result)


@bp.route("/api/tasks")
@require_basicauth
def api_tasks():
    return jsonify(tasks.all_tasks())


@bp.route("/api/tasks/<tid>")
@require_basicauth
def api_task(tid):
    t = tasks.get_task(tid)
    if not t:
        return jsonify({"error": "not found"}), 404
    return jsonify(t)


@bp.route("/start", methods=["POST"])
@require_basicauth
def start_server():
    mod = request.form.get("mod", "ra")
    if mod not in KNOWN_MODS:
        flash(f"Invalid mod: {mod}", "error")
        return redirect(url_for("ladderctl.index", _anchor="servers"))

    count = max(1, min(20, int(request.form.get("count", 1))))

    release = request.form.get("release", "release-20250330")
    if not _RELEASE_RE.match(release):
        flash(f"Invalid release tag: {release}", "error")
        return redirect(url_for("ladderctl.index", _anchor="servers"))

    base_dir = request.form.get("basedir", get_basedir())
    base_dir = os.path.abspath(base_dir)
    allowed_prefix = os.path.abspath(get_basedir())
    if not base_dir.startswith(allowed_prefix + os.sep) and base_dir != allowed_prefix:
        flash(f"basedir must be under {allowed_prefix}", "error")
        return redirect(url_for("ladderctl.index", _anchor="servers"))

    base_port = max(1024, int(request.form.get("base_port", get_config("LADDERCTL_BASE_PORT", "10300"))))
    container_name_prefix = request.form.get("container_name_prefix", "ladder_{mod}_")
    server_name_template = request.form.get(
        "server_name_template", "|oraladder.net| Competitive 1v1 Ladder Server {number}"
    )
    require_auth = request.form.get("require_auth", "True")
    enable_singleplayer = request.form.get("enable_singleplayer", "False")
    record_replays = request.form.get("record_replays", "True")
    replay_basedir = request.form.get("replay_basedir", "")
    force_rebuild = request.form.get("force_rebuild") == "on"
    connectivity = request.form.get("connectivity", "public")
    config_preset_name = request.form.get("config_preset_name", "")

    config = {}
    for key in CONFIG_FILE_KEYS:
        val = request.form.get(f"config_{key}")
        if val is not None:
            config[key] = val
        else:
            path = os.path.join(base_dir, key)
            try:
                with open(path) as f:
                    config[key] = f.read()
            except FileNotFoundError:
                config[key] = ""

    tid = tasks.new_task("Start servers", f"{count}x {mod} on {release}")
    tasks.run_background(
        tid,
        _bg_start_servers,
        (
            release,
            mod,
            count,
            base_dir,
            base_port,
            config,
            container_name_prefix,
            server_name_template,
            require_auth,
            enable_singleplayer,
            record_replays,
            replay_basedir,
            force_rebuild,
            connectivity,
            config_preset_name,
        ),
        app=current_app._get_current_object(),
    )
    flash(f"Task {tid} launched \u2013 building image and starting servers in background", "info")
    return redirect(url_for("ladderctl.index", _anchor="servers"))


def _bg_start_servers(
    tid,
    release,
    mod,
    count,
    base_dir,
    base_port,
    config,
    container_name_prefix="ladder_{mod}_",
    server_name_template="|oraladder.net| Competitive 1v1 Ladder Server {number}",
    require_auth="True",
    enable_singleplayer="False",
    record_replays="True",
    replay_basedir="",
    force_rebuild=False,
    connectivity="public",
    config_preset_name="",
):
    """Background task: ensure image exists, then launch containers."""

    def log(msg):
        tasks.append_log(tid, msg)

    log(f"Preparing image for {count}x {mod} server(s) on {release}")
    image_tag = ensure_image(release, mod, log_func=log, force=force_rebuild)

    client = docker_client()
    offset = 0
    if mod == "cnc":
        offset = 8

    write_config_files(base_dir, mod, config)

    resolved_prefix = container_name_prefix.replace("{mod}", mod)

    existing = [c for c in client.containers.list(all=True) if c.name and c.name.startswith(resolved_prefix)]
    existing_nums = set()
    for c in existing:
        try:
            existing_nums.add(int(c.name.split("_")[-1]))
        except (ValueError, IndexError):
            pass

    next_num = 1
    while next_num in existing_nums:
        next_num += 1

    used_host_ports = set()
    try:
        for c in client.containers.list(all=True):
            ports_info = c.attrs.get("NetworkSettings", {}).get("Ports", {})
            for bindings in ports_info.values():
                if bindings:
                    for b in bindings:
                        hp = b.get("HostPort")
                        if hp and hp.isdigit():
                            used_host_ports.add(int(hp))
    except Exception:
        pass

    # Prepare map pool environment variable
    mappool_raw = config.get(f"mappool_{mod}", "")
    mappool_list = ",".join(m.strip() for m in mappool_raw.replace(" ", "").split("\n") if m.strip())

    started = 0
    errors = []
    for i in range(count):
        number = next_num + i
        raw_name = resolved_prefix.replace("{number}", str(number))
        if "{number}" not in container_name_prefix:
            container_name = f"{raw_name.rstrip('_')}_{number}"
        else:
            container_name = raw_name
        port = base_port + number + offset
        while port in used_host_ports:
            port += 1
            log(f"Port {port-1} in use, trying {port}")
        used_host_ports.add(port)

        replay_host = replay_basedir or os.path.join(base_dir, "replays")
        replay_path = f"{replay_host}/{mod}/srv_{number}/{release}/"
        os.makedirs(replay_path, exist_ok=True)
        os.makedirs(f"{base_dir}/maps/{mod}/{release}/", exist_ok=True)

        try:
            old = client.containers.get(container_name)
            old.remove(force=True)
        except docker.errors.NotFound:
            pass

        try:
            client.containers.run(
                image=image_tag,
                name=container_name,
                detach=True,
                stdin_open=True,
                tty=True,
                ports={f"{port}/tcp": int(port) if connectivity == "public" else ("127.0.0.1", int(port))},
                labels={
                    "ladderctl.managed": "1",
                    "ladderctl.preset": config_preset_name or "",
                    "ladderctl.connectivity": connectivity,
                    "ladderctl.release": release,
                    "ladderctl.mod": mod,
                    "ladderctl.server_name": server_name_template.replace("{number}", str(number)),
                },
                environment={
                    "MOD": mod,
                    "Name": server_name_template.replace("{number}", str(number)),
                    "RequireAuthentication": require_auth,
                    "EnableSingleplayer": enable_singleplayer,
                    "RecordReplays": record_replays,
                    "ListenPort": str(port),
                    "TZ": "UTC",
                    "MapPool": mappool_list,
                },
                volumes={
                    replay_path: {
                        "bind": f"/home/openra/.config/openra/Replays/{mod}/{release}/",
                        "mode": "rw",
                    },
                    f"{base_dir}/maps/{mod}/{release}/": {
                        "bind": f"/home/openra/usr/lib/openra/mods/{mod}/maps/",
                        "mode": "rw",
                    },
                    f"{base_dir}/motd.{mod}.txt": {
                        "bind": "/home/openra/.config/openra/motd.txt",
                        "mode": "ro",
                    },
                    f"{base_dir}/banned_profiles": {
                        "bind": "/home/openra/banned_profiles",
                        "mode": "ro",
                    },
                },
                restart_policy={"Name": "always"},
            )
            try:
                c2 = client.containers.get(container_name)
                c2.exec_run("chown openra: -R /home/openra/.config/openra/", user="root")
            except Exception:
                pass
            log(f"Started {container_name}")
            started += 1
        except Exception as e:
            errors.append(str(e))
            log(f"ERROR: {container_name} \u2013 {e}")

    tasks.update_task(tid, status="success")
    if errors:
        msg = f"Started {started}/{count} servers. Errors: {'; '.join(errors)}"
        add_activity("Start servers partial", msg, "error")
    else:
        msg = f"Started {started} server(s)"
        add_activity("Servers started", msg, "success")
    log(msg)


def _container_action(container_name, action, label_past, label_fail):
    client = docker_client()
    if not is_ladderctl_container_name(container_name):
        add_activity(f"Container {label_fail}", f"{container_name} is not a ladderctl server", "error")
        flash(f"{container_name} is not a ladderctl server", "error")
        return redirect(url_for("ladderctl.index", _anchor="servers"))
    try:
        c = client.containers.get(container_name)
        getattr(c, action)()
        add_activity(f"Container {label_past}", container_name)
        flash(f"{label_past.capitalize()} {container_name}", "info")
    except docker.errors.NotFound:
        add_activity(f"Container {label_fail}", f"{container_name} not found", "error")
        flash(f"Container {container_name} not found", "error")
    return redirect(url_for("ladderctl.index", _anchor="servers"))


@bp.route("/<container_name>/stop", methods=["POST"])
@require_basicauth
def stop_container(container_name):
    return _container_action(container_name, "stop", "stopped", "stop failed")


@bp.route("/<container_name>/start", methods=["POST"])
@require_basicauth
def start_container(container_name):
    return _container_action(container_name, "start", "started", "start failed")


@bp.route("/<container_name>/restart", methods=["POST"])
@require_basicauth
def restart_container(container_name):
    return _container_action(container_name, "restart", "restarted", "restart failed")


@bp.route("/<container_name>/remove", methods=["POST"])
@require_basicauth
def remove_container(container_name):
    client = docker_client()
    if not is_ladderctl_container_name(container_name):
        add_activity("Container remove failed", f"{container_name} is not a ladderctl server", "error")
        flash(f"{container_name} is not a ladderctl server", "error")
        return redirect(url_for("ladderctl.index", _anchor="servers"))
    try:
        c = client.containers.get(container_name)
        c.remove(force=True)
        add_activity("Container removed", container_name)
        flash(f"Removed {container_name}", "info")
    except docker.errors.NotFound:
        add_activity("Container remove failed", f"{container_name} not found", "error")
        flash(f"Container {container_name} not found", "error")
    return redirect(url_for("ladderctl.index", _anchor="servers"))


@bp.route("/<container_name>/logs")
@require_basicauth
def container_logs(container_name):
    if not is_ladderctl_container_name(container_name):
        flash(f"{container_name} is not a ladderctl server", "error")
        return redirect(url_for("ladderctl.index", _anchor="servers"))
    client = docker_client()
    try:
        c = client.containers.get(container_name)
        log_data = c.logs(tail=200, timestamps=True).decode("utf-8", errors="replace")
        return render_template("logs.html", container_name=container_name, logs=log_data)
    except docker.errors.NotFound:
        flash(f"Container {container_name} not found", "error")
        return redirect(url_for("ladderctl.index", _anchor="servers"))
