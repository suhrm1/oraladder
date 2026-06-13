import datetime
import os
import shutil

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from ladderweb._flask_utils import require_basicauth, generate_csrf_token, validate_csrf
from ladderweb import api_system
from ladderweb.model import LadderDatabase

# ---------------------------------------------------------------------------
# Blueprint setup
# ---------------------------------------------------------------------------

admin_bp = Blueprint("admin", __name__, template_folder="templates/admin")


@admin_bp.context_processor
def _inject_csrf():
    """Make ``{{ csrf_token() }}`` available in every admin template."""
    return dict(csrf_token=generate_csrf_token)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_db() -> LadderDatabase:
    """Return the global database instance."""
    from ladderweb.__init__ import MainDB

    return MainDB


def _get_status(db: LadderDatabase):
    """Collect system-wide stats for the dashboard: game/account/banned
    counts, active season definitions, and relevant config values."""
    game_count = len(db.fetch_table("game"))
    account_count = len(db.fetch_table("accounts"))
    active_mods = list(db.get_seasons().keys())

    seasons = db.get_seasons()
    season_info = []
    for mod in active_mods:
        for sid, s in seasons[mod].items():
            season_info.append(
                {
                    "mod": mod,
                    "id": sid,
                    "title": s.title,
                    "active": s.active,
                    "start": s.start,
                    "end": s.end,
                    "algorithm": s.algorithm,
                    "replay_path": s.replay_path,
                }
            )

    banned = db.get_banned_profile_ids()

    config_keys = ["bans_file", "ra_default_replay_folder", "td_default_replay_folder", "deleted_replay_folder"]
    config_vals = {}
    for k in config_keys:
        v = db.get_config_value(k)
        if v:
            config_vals[k] = v

    return {
        "game_count": game_count,
        "account_count": account_count,
        "banned_count": len(banned),
        "mods": active_mods,
        "seasons": season_info,
        "config": config_vals,
    }


def _ensure_deleted_table(db):
    """Create the audit table for deleted replays if it does not exist."""
    db.exec(
        "CREATE TABLE IF NOT EXISTS _admin_deleted_replays ("
        "hash VARCHAR(64) NOT NULL PRIMARY KEY, "
        "`mod` VARCHAR(15) NOT NULL, "
        "start_time VARCHAR(32) NOT NULL, "
        "end_time VARCHAR(32) NOT NULL, "
        "filename TEXT NOT NULL, "
        "profile_id0 INTEGER NOT NULL, "
        "profile_id1 INTEGER NOT NULL, "
        "player0_name VARCHAR(255), "
        "player1_name VARCHAR(255), "
        "faction_0 VARCHAR(32) NOT NULL, "
        "faction_1 VARCHAR(32) NOT NULL, "
        "selected_faction_0 VARCHAR(32) NOT NULL, "
        "selected_faction_1 VARCHAR(32) NOT NULL, "
        "map_uid TEXT NOT NULL, "
        "map_title TEXT NOT NULL, "
        "deleted_at VARCHAR(32) NOT NULL"
        ")"
    )


def _resolve_player_names(db, profile_ids):
    """Map a set of profile IDs to their display names.

    Unknown IDs are rendered as ``#<id>``.
    """
    names = {}
    for pid in profile_ids:
        res = db.exec(f"SELECT profile_name FROM accounts WHERE profile_id={pid}", fetch=True)
        if res:
            names[pid] = res[0][0]
        else:
            names[pid] = f"#{pid}"
    return names


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@admin_bp.route("/")
@require_basicauth
def dashboard():
    """Show the admin dashboard with system status and action forms."""
    db = _get_db()
    status = _get_status(db)

    default_mod = status["mods"][0] if status["mods"] else "ra"
    default_replay_path = status["config"].get(f"{default_mod}_default_replay_folder", "")

    season_ids = {}
    for mod in status["mods"]:
        ids = sorted(set(s["id"] for s in status["seasons"] if s["mod"] == mod and s["id"]))
        season_ids[mod] = ids

    return render_template(
        "admin_dashboard.html",
        status=status,
        default_mod=default_mod,
        default_replay_path=default_replay_path,
        season_ids=season_ids,
    )


# ---------------------------------------------------------------------------
# System action routes
# ---------------------------------------------------------------------------


@admin_bp.route("/parse_replays", methods=["POST"])
@require_basicauth
@validate_csrf
def parse_replays():
    """Scan a replay directory for new `.orarep` files and ingest them."""
    db = _get_db()
    mod = request.form.get("mod", "ra")
    max_age = request.form.get("max_file_age_days")
    if max_age:
        max_age = int(max_age)

    replay_path = request.form.get("replay_path", "").strip()
    if not replay_path:
        replay_path = db.get_config_value(f"{mod}_default_replay_folder") or ""

    result, _ = api_system.parse_replays(
        database=db,
        mod=mod,
        replay_directory=replay_path,
        max_file_modified_days=max_age,
        skip_known_files=True,
    )
    flash(f"Parsed {result['replays_parsed']} replays in {result['processing_time']}", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/update_rankings", methods=["POST"])
@require_basicauth
@validate_csrf
def update_rankings():
    """Recalculate ratings, rankings, and highscores for one or all seasons."""
    db = _get_db()
    mod = request.form.get("mod")
    season_id = request.form.get("season_id")
    seasons = db.get_seasons()

    if mod:
        mods = [mod]
    else:
        mods = list(seasons.keys())

    for m in mods:
        if season_id:
            season_list = [(season_id, seasons[m][season_id])]
        else:
            season_list = [(sid, s) for sid, s in seasons[m].items() if sid]
        for sid, s in season_list:
            api_system.update_season_ratings(database=db, season=s)
            api_system.update_season_ranking(database=db, season=s)
            api_system.update_highscore(database=db, mod_id=m, season_group=s.group)
            db.update_season_history(mod_id=m, season_id=sid)
            db.update_player_season_history(mod_id=m, season_id=sid, season_group=s.group)

    flash("Rankings updated", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/rotate_season", methods=["POST"])
@require_basicauth
@validate_csrf
def rotate_season():
    """Close the current 2-month season and open a fresh one."""
    db = _get_db()
    mod = request.form.get("mod") or None
    api_system.rotate_current_2m_season(db=db, mod=mod)
    if mod:
        db.update_season_history(mod_id=mod)

    flash("Season rotated", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/update_profiles", methods=["POST"])
@require_basicauth
@validate_csrf
def update_profiles():
    """Refresh player names and avatar URLs from the OpenRA Forum API."""
    db = _get_db()
    result = api_system.update_player_profiles(database=db)
    flash(f"Updated {result['update_count']} profiles ({result['error_count']} errors)", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/system_refresh", methods=["POST"])
@require_basicauth
@validate_csrf
def system_refresh():
    """Full pipeline: parse replays → update rankings → rotate seasons
    for every mod configured in the system."""
    db = _get_db()
    seasons = db.get_seasons()
    for mod in seasons.keys():
        result, _ = api_system.parse_replays(database=db, mod=mod, replay_directory="")
        if result["replays_parsed"] > 0:
            for sid in seasons[mod].keys():
                if sid:
                    s = seasons[mod][sid]
                    api_system.update_season_ratings(database=db, season=s)
                    api_system.update_season_ranking(database=db, season=s)
                    api_system.update_highscore(database=db, mod_id=mod, season_group=s.group)
                    db.update_season_history(mod_id=mod, season_id=sid)
                    db.update_player_season_history(mod_id=mod, season_id=sid, season_group=s.group)
        api_system.rotate_current_2m_season(db=db, mod=mod)

    flash("System refresh complete", "info")
    return redirect(url_for("admin.dashboard"))


# ---------------------------------------------------------------------------
# Replay management
# ---------------------------------------------------------------------------


@admin_bp.route("/replays")
@require_basicauth
def replays():
    """List active (non-deleted) replays with optional filters.

    Supports up to 200 results ordered by end time descending.
    Filters: mod, player name, map title, date range.
    """
    db = _get_db()

    mod = request.args.get("mod", "")
    player = request.args.get("player", "")
    map_title = request.args.get("map_title", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    conditions = []
    if mod:
        conditions.append(f"g.`mod`='{mod}'")
    if date_from:
        conditions.append(f"g.end_time>='{date_from}'")
    if date_to:
        conditions.append(f"g.end_time<='{date_to} 23:59:59'")
    if map_title:
        conditions.append(f"g.map_title LIKE '%{map_title}%'")

    join_clause = ""
    player_condition = ""
    if player:
        join_clause = (
            "LEFT JOIN accounts a0 ON g.profile_id0 = a0.profile_id "
            "LEFT JOIN accounts a1 ON g.profile_id1 = a1.profile_id"
        )
        player_condition = f"AND (a0.profile_name LIKE '%{player}%' OR a1.profile_name LIKE '%{player}%')"

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql = (
        f"SELECT DISTINCT g.hash, g.`mod`, g.start_time, g.end_time, g.filename, "
        f"g.profile_id0, g.profile_id1, g.faction_0, g.faction_1, "
        f"g.selected_faction_0, g.selected_faction_1, g.map_uid, g.map_title "
        f"FROM game g {join_clause} WHERE {where_clause} {player_condition} "
        f"ORDER BY g.end_time DESC LIMIT 200"
    )
    games = db.exec(sql, fetch=True)
    rows = [dict(r._mapping) for r in games]

    profile_ids = set()
    for r in rows:
        profile_ids.add(r["profile_id0"])
        profile_ids.add(r["profile_id1"])
    names = _resolve_player_names(db, profile_ids)
    for r in rows:
        r["player0_name"] = names.get(r["profile_id0"], f"#{r['profile_id0']}")
        r["player1_name"] = names.get(r["profile_id1"], f"#{r['profile_id1']}")

    mods = db.exec("SELECT DISTINCT `mod` FROM game ORDER BY `mod`", fetch=True)
    mods = [m[0] for m in mods]

    return render_template(
        "admin_replays.html",
        tab="active",
        replays=rows,
        mods=mods,
        filters={"mod": mod, "player": player, "map_title": map_title, "date_from": date_from, "date_to": date_to},
    )


@admin_bp.route("/replays/deleted")
@require_basicauth
def deleted_replays():
    """List previously deleted replays from the audit table.

    Same filter UI as active replays, sourced from
    ``_admin_deleted_replays`` instead.
    """
    db = _get_db()
    _ensure_deleted_table(db)

    mod = request.args.get("mod", "")
    player = request.args.get("player", "")
    map_title = request.args.get("map_title", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    conditions = []
    if mod:
        conditions.append(f"d.`mod`='{mod}'")
    if date_from:
        conditions.append(f"d.end_time>='{date_from}'")
    if date_to:
        conditions.append(f"d.end_time<='{date_to} 23:59:59'")
    if map_title:
        conditions.append(f"d.map_title LIKE '%{map_title}%'")
    if player:
        conditions.append(f"(d.player0_name LIKE '%{player}%' OR d.player1_name LIKE '%{player}%')")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql = f"SELECT * FROM _admin_deleted_replays d WHERE {where_clause} ORDER BY d.deleted_at DESC LIMIT 200"
    games = db.exec(sql, fetch=True)
    rows = [dict(r._mapping) for r in games]

    mods = db.exec("SELECT DISTINCT `mod` FROM _admin_deleted_replays ORDER BY `mod`", fetch=True)
    mods = [m[0] for m in mods]

    return render_template(
        "admin_replays.html",
        tab="deleted",
        replays=rows,
        mods=mods,
        filters={"mod": mod, "player": player, "map_title": map_title, "date_from": date_from, "date_to": date_to},
    )


@admin_bp.route("/replays/delete", methods=["POST"])
@require_basicauth
@validate_csrf
def delete_replays():
    """Delete selected replays (via ``replay_hashes`` checkboxes).

    Requires re-entering the admin password (posted as
    ``admin_password``) for confirmation.  Deleted replay metadata is
    saved to the ``_admin_deleted_replays`` audit table and the backing
    ``.orarep`` file is moved to the archive folder by
    :func:`api_system.delete_replay`.
    """
    password = request.form.get("admin_password", "")
    expected = current_app.config.get("LADDER_ADMIN_PASSWORD", "")
    if password != expected:
        flash("Wrong admin password — deletion cancelled", "error")
        return redirect(url_for("admin.replays"))

    db = _get_db()
    hashes = request.form.getlist("replay_hashes")
    deleted = 0
    errors = 0

    for h in hashes:
        game_data = db.exec(f"SELECT * FROM game WHERE hash='{h}'", fetch=True)
        if not game_data:
            errors += 1
            continue

        game = dict(game_data[0]._mapping)
        result = api_system.delete_replay(database=db, hash=h)
        if result:
            _ensure_deleted_table(db)

            profile_ids = {game["profile_id0"], game["profile_id1"]}
            names = _resolve_player_names(db, profile_ids)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            db.exec(
                "INSERT INTO _admin_deleted_replays "
                "(hash, `mod`, start_time, end_time, filename, "
                "profile_id0, profile_id1, player0_name, player1_name, "
                "faction_0, faction_1, selected_faction_0, selected_faction_1, "
                "map_uid, map_title, deleted_at) VALUES ("
                f"'{game['hash']}', '{game['mod']}', '{game['start_time']}', '{game['end_time']}', "
                f"'{game['filename']}', {game['profile_id0']}, {game['profile_id1']}, "
                f"'{names.get(game['profile_id0'], '#' + str(game['profile_id0']))}', "
                f"'{names.get(game['profile_id1'], '#' + str(game['profile_id1']))}', "
                f"'{game['faction_0']}', '{game['faction_1']}', "
                f"'{game['selected_faction_0']}', '{game['selected_faction_1']}', "
                f"'{game['map_uid']}', '{game['map_title']}', "
                f"'{now}'"
                f")"
            )
            deleted += 1
        else:
            errors += 1

    flash(f"Deleted {deleted} replays" + (f", {errors} failed" if errors else ""), "info")
    return redirect(url_for("admin.replays"))


@admin_bp.route("/replays/undelete", methods=["POST"])
@require_basicauth
@validate_csrf
def undelete_replays():
    """Restore previously deleted replays.

    Looks up each hash in the ``_admin_deleted_replays`` audit table,
    restores the archived ``.orarep`` file, re-inserts the row into
    the ``game`` table, and removes the audit entry.
    """
    password = request.form.get("admin_password", "")
    expected = current_app.config.get("LADDER_ADMIN_PASSWORD", "")
    if password != expected:
        flash("Wrong admin password — undelete cancelled", "error")
        return redirect(url_for("admin.deleted_replays"))

    db = _get_db()
    hashes = request.form.getlist("replay_hashes")
    restored = 0
    errors = 0

    for h in hashes:
        deleted_data = db.exec(f"SELECT * FROM _admin_deleted_replays WHERE hash='{h}'", fetch=True)
        if not deleted_data:
            errors += 1
            continue

        entry = dict(deleted_data[0]._mapping)

        # Check the game doesn't already exist in the live table
        existing = db.exec(f"SELECT 1 FROM game WHERE hash='{h}'", fetch=True)
        if existing:
            # Already restored — just clean up the audit row
            db.exec(f"DELETE FROM _admin_deleted_replays WHERE hash='{h}'")
            restored += 1
            continue

        # Restore the .orarep file from the archive folder
        deleted_replay_folder = db.get_config_value("deleted_replay_folder")
        archived_path = os.path.join(deleted_replay_folder, os.path.basename(entry["filename"]))
        try:
            os.makedirs(os.path.dirname(entry["filename"]), exist_ok=True)
            shutil.copy2(src=archived_path, dst=entry["filename"])
            os.remove(archived_path)
        except FileNotFoundError:
            pass  # file may have been manually cleaned; still restore DB entry
        except OSError:
            pass

        # Re-insert into the game table
        db.exec(
            "INSERT INTO game (hash, `mod`, start_time, end_time, filename, "
            "profile_id0, profile_id1, faction_0, faction_1, "
            "selected_faction_0, selected_faction_1, map_uid, map_title) VALUES ("
            f"'{entry['hash']}', '{entry['mod']}', '{entry['start_time']}', '{entry['end_time']}', "
            f"'{entry['filename']}', {entry['profile_id0']}, {entry['profile_id1']}, "
            f"'{entry['faction_0']}', '{entry['faction_1']}', "
            f"'{entry['selected_faction_0']}', '{entry['selected_faction_1']}', "
            f"'{entry['map_uid']}', '{entry['map_title']}'"
            f")"
        )

        # Remove the audit entry
        db.exec(f"DELETE FROM _admin_deleted_replays WHERE hash='{h}'")

        restored += 1

    flash(f"Restored {restored} replays" + (f", {errors} failed" if errors else ""), "info")
    return redirect(url_for("admin.deleted_replays"))
