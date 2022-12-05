#
# Copyright (C) 2020-2022
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import re
import colorsys
import os
import os.path as op
import json
from sqlite3 import Connection
from typing import Optional, Tuple

import numpy as np
import sqlite3
from datetime import date, timedelta
from flask import (
    Flask,
    escape,
    g,
    jsonify,
    render_template,
    request,
    send_file,
    url_for,
)

from ladderweb.seasons import load_yaml_season_config_from_directory, Season
from .mods import mods

# XXX: store in a file probably
_cfg = dict(
    min_datapoints=10,
    datapoints=50,
)


def _get_request_params() -> Tuple[str, str, str]:
    """Extract HTTP request parameters for endpoint/URL route, mod, period."""
    _allowed_mods = app.config["ALLOWED_MODS"]
    _seasons = app.config["LADDER_SEASONS"]
    endpoint = request.endpoint
    mod = request.args.get("mod", _allowed_mods[0])
    if mod not in _allowed_mods:
        mod = _allowed_mods[0]
    _allowed_periods = list(_seasons[mod].keys())
    _default_period_key = app.config.get("LADDER_DEFAULT_SEASON_KEY", "2m")
    period = request.args.get("period", _default_period_key)
    if period not in _allowed_periods:
        period = _default_period_key
    return endpoint, mod, period


def _filter_available_databases(seasons_dict: dict):
    """Filters out all seasons/periods from the dictionary for which no database exists

    Input dictionary should be loaded using seasons.load_yaml_season_config_from_directory method.
    """
    to_delete = []
    for mod, _seasons in seasons_dict.items():
        for season_name, season in _seasons.items():
            if season is None:
                to_delete.append((mod, season_name))
                continue
            file = op.join(app.instance_path, season.database_file)
            if not op.exists(file):
                to_delete.append((mod, season_name))
    for mod, season_name in to_delete:
        del seasons_dict[mod][season_name]
    return seasons_dict


def _db_get(db_filename: Optional[str] = None) -> Connection:
    if db_filename is not None:
        dbname = db_filename
        db = op.join(app.instance_path, dbname)
        conn = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn
    elif "db" not in g:
        _, mod, period = _get_request_params()
        _season: Season = app.config.get("LADDER_SEASONS")[mod][period]
        dbname = _season.database_file
        db = op.join(app.instance_path, dbname)
        app.logger.debug(f"Opening database file {db}")
        g.db = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def _db_close(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def create_app():
    app = Flask(__name__)
    app.teardown_appcontext(_db_close)
    return app


app = create_app()
app.config.from_prefixed_env()
app.config["LADDER_SEASONS"] = _filter_available_databases(load_yaml_season_config_from_directory(app.instance_path))
app.config["ALLOWED_MODS"] = list(app.config["LADDER_SEASONS"].keys())
app.logger.debug(f"Loaded available mods and seasons: {app.config['LADDER_SEASONS']}")


@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == "static":
        filename = values.get("filename", None)
        if filename:
            file_path = op.join(app.root_path, endpoint, filename)
            values["q"] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


def _args_url(**args):
    base_args = dict()
    period = request.args.get("period")
    mod = request.args.get("mod")
    if period is not None:
        base_args["period"] = period
    if mod is not None:
        base_args["mod"] = mod
    base_args.update(args)
    param_str = "&".join(f"{k}={v}" for k, v in base_args.items())
    return ("?" + param_str) if param_str else ""


def _get_menu(**args):
    cur_endpoint, cur_mod, cur_period = _get_request_params()
    ret = dict(
        pages=[
            dict(
                caption=caption,
                url=url_for(endpoint) + _args_url(),
                active=endpoint == cur_endpoint,
            )
            for caption, endpoint in (
                ("Leaderboard", "leaderboard"),
                ("Latest games", "latest_games"),
                ("Global stats", "globalstats"),
                ("Information", "info"),
            )
        ],
    )

    mods_menu = [
        dict(
            caption=mod_info["label"],
            url=url_for(cur_endpoint, **args) + _args_url(mod=mod),
            icon=url_for("static", filename=mod_info["icon"]) if "icon" in mod_info else None,
            active=mod == cur_mod,
        )
        for mod, mod_info in mods.items()
    ]
    # Add the mod selection to the menu only if there is more than one
    if len(mods_menu) > 1:
        ret["mods"] = mods_menu

    period_pages = {"leaderboard", "latest_games", "player", "globalstats"}

    periods: dict[Season] = app.config["LADDER_SEASONS"][cur_mod]
    period_options = []
    for period in periods.values():
        period_options.append((period.title, period.id))

    if cur_endpoint in period_pages:
        ret["period"] = [
            dict(
                caption=caption,
                url=url_for(cur_endpoint, **args) + _args_url(period=period),
                active=period == cur_period,
            )
            for caption, period in period_options
        ]

    return ret


@app.route("/")
def leaderboard():
    menu = _get_menu()
    ajax_url = url_for("leaderboard_js") + _args_url()
    _, cur_mod, cur_period = _get_request_params()
    season: Season = app.config["LADDER_SEASONS"][cur_mod][cur_period]
    print(f"Season: {season}")
    return render_template(
        "leaderboard.html",
        navbar_menu=menu,
        ajax_url=ajax_url,
        period_info=season.get_info() if cur_period != "all" else None,
        mod_id=cur_mod,
    )


@app.route("/leaderboard-js")
def leaderboard_js():
    db = _db_get()
    cur = db.execute(
        """
        SELECT
            profile_id,
            profile_name,
            avatar_url,
            wins,
            losses,
            prv_rating,
            rating
        FROM players
        WHERE rating > 0 AND NOT banned
        ORDER BY rating DESC
        """
    )

    rows = []
    for i, (profile_id, profile_name, avatar_url, wins, losses, prv_rating, rating) in enumerate(cur, 1):
        rows.append(
            dict(
                row_id=i,
                player=dict(
                    name=escape(profile_name),
                    url=url_for("player", profile_id=profile_id) + _args_url(),
                    avatar_url=avatar_url,
                ),
                rating=dict(
                    value=rating,
                    diff=rating - prv_rating,
                ),
                played=wins + losses,
                wins=wins,
                losses=losses,
                winrate=wins / (wins + losses) * 100,
            )
        )

    return jsonify(rows)


@app.route("/latest")
def latest_games():
    _, cur_mod, cur_period = _get_request_params()
    season = app.config["LADDER_SEASONS"][cur_mod][cur_period]
    menu = _get_menu()
    ajax_url = url_for("latest_games_js") + _args_url()
    return render_template(
        "latest.html", navbar_menu=menu, ajax_url=ajax_url, period_info=season.get_info(), mod_id=cur_mod
    )


_tag_regex = re.compile(r"\s*\[[^\]]*\]")


def _stripped_map_name(map_name):
    return _tag_regex.sub("", map_name).strip()


@app.route("/latest-js")
def latest_games_js():
    _, cur_mod, _ = _get_request_params()
    db = _db_get()
    cur = db.execute(
        """
        SELECT
            hash,
            end_time,
            strftime('%M:%S', julianday(end_time) - julianday(start_time)) AS duration,
            profile_id0,
            profile_id1,
            rating_0 - rating_0_prv AS diff0,
            rating_1 - rating_1_prv AS diff1,
            p0.profile_name AS p0_name,
            p1.profile_name AS p1_name,
            p0.banned AS p0_banned,
            p1.banned AS p1_banned,
            map_title
        FROM outcomes o
        LEFT JOIN players p0 ON p0.profile_id = o.profile_id0
        LEFT JOIN players p1 ON p1.profile_id = o.profile_id1
        ORDER BY o.end_time DESC
        """
    )
    matches = cur.fetchall()
    cur.close()

    games = []
    for match in matches:
        game = dict(
            replay=dict(
                hash=match["hash"],
                url=url_for("replay", replay_hash=match["hash"]) + _args_url(),
                supports_analysis=mods[cur_mod].get("supports_analysis", False),
            )
            if not any((match["p0_banned"], match["p1_banned"]))
            else None,
            date=match["end_time"],
            duration=match["duration"],
            map=_stripped_map_name(match["map_title"]),
            p0=dict(
                name=escape(match["p0_name"]),
                url=url_for("player", profile_id=match["profile_id0"]) + _args_url(),
                diff=match["diff0"],
            )
            if not match["p0_banned"]
            else None,
            p1=dict(
                name=escape(match["p1_name"]),
                url=url_for("player", profile_id=match["profile_id1"]) + _args_url(),
                diff=match["diff1"],
            )
            if not match["p1_banned"]
            else None,
        )
        games.append(game)

    return jsonify(games)


def _scaled(a, m):
    n = len(a)
    nr = range(n)
    mr = [x * n / m for x in range(m)]
    return [round(x) for x in np.interp(mr, nr, a)]


def _get_player_ratings(db, profile_id):
    cur = db.execute(
        """
        SELECT
            profile_id0,
            profile_id1,
            rating_0,
            rating_1
        FROM outcomes o
        LEFT JOIN players p0 ON p0.profile_id = o.profile_id0
        LEFT JOIN players p1 ON p1.profile_id = o.profile_id1
        WHERE :pid IN (o.profile_id0, o.profile_id1)
        ORDER BY o.end_time""",
        dict(pid=profile_id),
    )
    ratings = []
    for match in cur:
        if match["profile_id0"] == profile_id:
            rating = match["rating_0"]
        elif match["profile_id1"] == profile_id:
            rating = match["rating_1"]
        else:
            continue  # XXX shouldn't happen, assert?
        ratings.append(rating)
    cur.close()

    ratings = ratings[_cfg["min_datapoints"] :]
    if not ratings:
        return [], []

    datapoints = _cfg["datapoints"]
    rating_labels = [str("") for x in range(datapoints)]
    rating_labels = json.dumps(rating_labels)

    ratings = _scaled(ratings, datapoints)  # rescale all ratings to a fixed number of data points
    rating_data = json.dumps(ratings)

    return dict(
        labels=rating_labels,
        data=rating_data,
    )


def _get_player_season_history(mod, profile_id):
    _seasons: dict[Season] = app.config["LADDER_SEASONS"][mod]
    player_season_history = []
    for season_name, season in _seasons.items():
        db_file = op.join(app.instance_path, season.database_file)
        with _db_get(db_file) as db:
            row = db.execute(
                f"""select rating, wins, losses, (wins+losses) as games,
                (
                    SELECT strftime('%M:%S', AVG(julianday(end_time) - julianday(start_time)))
                    FROM outcomes
                    WHERE {profile_id} IN (profile_id0, profile_id1)
                ) AS avg_game_duration
                from players where profile_id={profile_id}"""
            ).fetchone()
            if row is not None:
                stats = dict(row)
                rank = db.execute(
                    f"""select count(profile_id) from players
                    where rating>{stats['rating']} AND NOT banned"""
                ).fetchone()[0]
                players = db.execute(f"""select count(profile_id) from players""").fetchone()[0]

                stats["rank"] = rank + 1
                stats["players"] = players
                stats["trophy"] = ""
                if rank < 3:
                    stats["trophy"] = ["🥇", "🥈", "🥉"][rank]
                stats["ratio"] = "{:.2f}%".format(stats["wins"] / stats["games"] * 100)
                stats["season"] = season.get_info()

                player_season_history.append(stats)

    return player_season_history


def _get_player_info(db, profile_id):
    cur = db.execute(
        """
        SELECT
        *, (
            SELECT COUNT(*)
            FROM players
            WHERE rating >= (SELECT rating FROM players WHERE profile_id=:pid) AND NOT banned
        ) AS rank,
        (
            SELECT strftime('%M:%S', AVG(julianday(end_time) - julianday(start_time)))
            FROM outcomes
            WHERE :pid IN (profile_id0, profile_id1)
        ) AS avg_game_duration,
        (
            SELECT MIN(end_time) FROM outcomes
            WHERE :pid IN (profile_id0, profile_id1)
        ) AS first_game,
        (
            SELECT MAX(end_time) FROM outcomes
            WHERE :pid IN (profile_id0, profile_id1)
        ) AS last_game
        FROM players WHERE profile_id=:pid AND NOT banned
        LIMIT 1""",
        dict(pid=profile_id),
    )
    player = cur.fetchone()
    cur.close()
    return player


def _get_player_faction_stats(db, profile_id):
    cur = db.execute(
        """
        SELECT COUNT(*)/2 AS count,
            (CASE
            WHEN o.profile_id0=:pid THEN selected_faction_0
            WHEN o.profile_id1=:pid THEN selected_faction_1
        END) AS faction
        FROM outcomes o LEFT JOIN players p ON p.profile_id IN (o.profile_id0, o.profile_id1)
        WHERE :pid IN (o.profile_id0, o.profile_id1)
        GROUP BY faction""",
        dict(pid=profile_id),
    )
    hist = [(r["faction"], r["count"]) for r in cur]
    cur.close()
    faction_names, faction_data = zip(*hist)
    faction_colors = _get_colors(len(hist))
    return dict(
        names=list(faction_names),
        data=list(faction_data),
        total=sum(faction_data),
        colors=faction_colors,
    )


def _get_player_map_stats(db, profile_id):
    cur = db.execute(
        """
        SELECT COUNT(*) AS count, map_title FROM outcomes WHERE profile_id0=:pid GROUP BY map_title""",
        dict(pid=profile_id),
    )
    hist_wins = {r["map_title"]: r["count"] for r in cur}
    cur.close()

    cur = db.execute(
        """
        SELECT -COUNT(*) AS count, map_title FROM outcomes WHERE profile_id1=:pid GROUP BY map_title""",
        dict(pid=profile_id),
    )
    hist_losses = {r["map_title"]: r["count"] for r in cur}
    cur.close()

    map_names = sorted(list(set(hist_wins.keys()) | set(hist_losses.keys())))
    map_win_data = [hist_wins.get(m, 0) for m in map_names]
    map_loss_data = [hist_losses.get(m, 0) for m in map_names]
    return dict(
        names=map_names,
        win_data=map_win_data,
        loss_data=map_loss_data,
    )


@app.route("/player-games-js/<int:profile_id>")
def player_games_js(profile_id):
    _, cur_mod, _ = _get_request_params()
    db = _db_get()
    cur = db.execute(
        """
        SELECT
            hash,
            end_time,
            strftime('%M:%S', julianday(end_time) - julianday(start_time)) AS duration,
            profile_id0,
            profile_id1,
            rating_0 - rating_0_prv AS diff0,
            rating_1 - rating_1_prv AS diff1,
            p0.profile_name AS p0_name,
            p1.profile_name AS p1_name,
            p0.banned AS p0_banned,
            p1.banned AS p1_banned,
            map_title
        FROM outcomes o
        LEFT JOIN players p0 ON p0.profile_id = o.profile_id0
        LEFT JOIN players p1 ON p1.profile_id = o.profile_id1
        WHERE :pid in (o.profile_id0, o.profile_id1)
        ORDER BY o.end_time DESC
        """,
        dict(pid=profile_id),
    )
    games = []
    for match in cur:
        if match["profile_id0"] == profile_id:
            diff = match["diff0"]
            opponent = escape(match["p1_name"])
            opponent_id = match["profile_id1"]
            opponent_banned = match["p1_banned"]
            banned = match["p0_banned"]
            outcome = "Won"
        elif match["profile_id1"] == profile_id:
            diff = match["diff1"]
            opponent = escape(match["p0_name"])
            opponent_id = match["profile_id0"]
            opponent_banned = match["p0_banned"]
            banned = match["p1_banned"]
            outcome = "Lost"
        else:
            continue  # XXX shouldn't happen, assert?
        if banned:
            break
        game = dict(
            date=match["end_time"],
            opponent=dict(
                name=opponent,
                url=url_for("player", profile_id=opponent_id) + _args_url(),
                # avatar_url=avatar_url,
            )
            if not opponent_banned
            else None,
            map=_stripped_map_name(match["map_title"]),
            outcome=dict(
                desc=outcome,
                diff=diff,
            ),
            duration=match["duration"],
            replay=dict(
                hash=match["hash"],
                url=url_for("replay", replay_hash=match["hash"]) + _args_url(),
                supports_analysis=mods[cur_mod].get("supports_analysis", False),
            )
            if not opponent_banned
            else None,
        )
        games.append(game)
    cur.close()

    return jsonify(games)


@app.route("/player/<int:profile_id>")
def player(profile_id):
    db = _db_get()
    _, cur_mod, cur_period = _get_request_params()
    alltime: Season = app.config["LADDER_SEASONS"][cur_mod]["all"]
    alltime_db = _db_get(alltime.database_file)
    current: Season = app.config["LADDER_SEASONS"][cur_mod][cur_period]
    menu = _get_menu(profile_id=profile_id)

    # load current period database first to see if player was active during this
    player = _get_player_info(db, profile_id)
    if not player:
        return render_template("noplayer.html", navbar_menu=menu, profile_id=profile_id, mod_id=cur_mod)

    # load all-time player data for all-time information
    player = _get_player_info(alltime_db, profile_id)
    player = dict(player)

    player["seasons"] = _get_player_season_history(mod=cur_mod, profile_id=profile_id)
    ajax_url = url_for("player_games_js", profile_id=profile_id) + _args_url()

    return render_template(
        "player.html",
        navbar_menu=menu,
        player=player,
        ajax_url=ajax_url,
        rating_stats=_get_player_ratings(db, profile_id),
        faction_stats=_get_player_faction_stats(db, profile_id),
        map_stats=_get_player_map_stats(db, profile_id),
        mod_id=cur_mod,
        season_info=current.get_info(),
    )


def _hexc(fc):
    return "#" + "".join("%02X" % int(fc[i] * 255) for i in range(3))


def _get_colors(n):
    return [_hexc(colorsys.hls_to_rgb(i / n, 0.4, 0.6)) for i in range(n)]


def _get_global_faction_stats(db):
    hist = {}

    # XXX: clumsy, patch welcome
    for i in range(2):
        cur = db.execute(
            f"SELECT COUNT(*) AS count, selected_faction_{i} AS faction FROM outcomes GROUP BY selected_faction_{i}"
        )
        hist.update({r["faction"]: r["count"] for r in cur})
        cur.close()
    hist = hist.items()

    if not hist:
        return [], [], []

    faction_names, faction_data = zip(*hist)
    faction_colors = _get_colors(len(hist))
    return dict(
        names=list(faction_names),
        data=list(faction_data),
        total=sum(faction_data),
        colors=faction_colors,
    )


def _get_global_map_stats(db):
    cur = db.execute("SELECT COUNT(*) AS count, map_title FROM outcomes GROUP BY map_title")
    hist = [(r["map_title"], r["count"]) for r in cur]
    cur.close()

    if not hist:
        return [], [], []

    map_names, map_data = zip(*hist)
    map_colors = _get_colors(len(hist))
    return dict(
        names=list(map_names),
        data=list(map_data),
        total=sum(map_data),
        colors=map_colors,
    )


def _get_activity_stats(db, start_date: Optional[date] = None, end_date: Optional[date] = None):
    cur = db.execute(
        """
        SELECT
            date(end_time) as date,
            COUNT(*) as count
        FROM outcomes
        GROUP BY date
        ORDER BY date ASC"""
    )
    outcomes_per_day = cur.fetchall()
    if not outcomes_per_day:
        return dict(dates=None, data=None, games_per_day=0)

    if start_date is None:
        start_date = date.fromisoformat(outcomes_per_day[0]["date"])
    if end_date is None:
        end_date = date.fromisoformat(outcomes_per_day[-1:][0]["date"])
    nb_days = (end_date - start_date).days
    all_days = [(start_date + timedelta(n)).strftime("%Y-%m-%d") for n in range(nb_days + 1)]
    db_records = {o["date"]: o["count"] for o in outcomes_per_day}
    records = {d: db_records.get(d, 0) for d in all_days}

    return dict(
        dates=list(records.keys()),
        data=list(records.values()),
        games_per_day=sum(records.values()) / len(records),
    )


@app.route("/globalstats")
def globalstats():
    db = _db_get()

    cur = db.execute(
        """
        SELECT
            COUNT(*) AS nb_games,
            strftime('%M:%S', AVG(julianday(end_time) - julianday(start_time))) AS avg_duration
        FROM outcomes"""
    )
    data = cur.fetchone()
    nb_games = data["nb_games"]
    avg_duration = data["avg_duration"]
    cur.close()

    cur = db.execute("SELECT COUNT(*) AS nb_players FROM players WHERE NOT banned")
    nb_players = cur.fetchone()["nb_players"]
    cur.close()

    menu = _get_menu()
    _, cur_mod, cur_period = _get_request_params()
    season = app.config["LADDER_SEASONS"][cur_mod][cur_period]
    return render_template(
        "globalstats.html",
        navbar_menu=menu,
        faction_stats=_get_global_faction_stats(db),
        map_stats=_get_global_map_stats(db),
        activity_stats=_get_activity_stats(db),
        nb_games=nb_games,
        nb_players=nb_players,
        avg_duration=avg_duration,
        period_info=season.get_info() if cur_period != "all" else None,
        mod_id=cur_mod,
    )


@app.route("/about")
@app.route("/info")
def info():
    menu = _get_menu()
    _, cur_mod, cur_period = _get_request_params()
    season = app.config["LADDER_SEASONS"][cur_mod]["2m"]
    return render_template(
        "info.html",
        navbar_menu=menu,
        period_info=season.get_info(),
        mod=mods[cur_mod],
        mod_id=cur_mod,
    )


@app.route("/replay/<replay_hash>")
def replay(replay_hash):
    db = _db_get()
    cur = db.execute("SELECT filename FROM outcomes WHERE hash=:hash", dict(hash=replay_hash))
    fullpath = cur.fetchone()["filename"]
    cur.close()
    return send_file(fullpath, as_attachment=True)
