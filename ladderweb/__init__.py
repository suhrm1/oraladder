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
import datetime
import json
import os
import os.path as op
from logging import Logger
from typing import Tuple, Union, Optional
from concurrent.futures import ThreadPoolExecutor

from flask import (
    escape,
    jsonify,
    render_template,
    request,
    send_file,
    url_for,
    g,
    Response,
)

from ladderweb import api_system
from ladderweb.model.seasons import Season
from ladderweb._flask_utils import api_key_authn, create_app
from ladderweb.model import LadderDatabase
from ladderweb.mods import mods
from ladderweb.utils import (
    _get_colors,
    _get_global_faction_stats,
    _get_global_map_stats,
    _get_activity_stats,
    _stripped_map_name,
    _get_player_ratings,
    _get_player_faction_stats,
    _get_player_map_stats,
    cast_boolean,
)


def _get_request_params() -> Tuple[str, str, str]:
    """Extract HTTP request parameters for endpoint/URL route, mod, period."""
    _seasons = MainDB.get_seasons()
    _allowed_mods = list(_seasons.keys())
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


# Initialize the Flask application
app = create_app()
logger: Logger = app.logger

db_settings = {
    "bans_file": app.config.get("LADDER_BANS_FILE", "instance/banned_profiles"),
    "ra_default_replay_folder": app.config.get("LADDER_RA_DEFAULT_REPLAY_FOLDER", "/replays/ra"),
    "td_default_replay_folder": app.config.get("LADDER_TD_DEFAULT_REPLAY_FOLDER", "/replays/td"),
    "deleted_replay_folder": app.config.get("LADDER_DELETED_REPLAY_FOLDER", app.instance_path + "/deleted_replays/"),
}

MainDB = LadderDatabase(
    connection_string=app.config.get("LADDER_MAIN_DATABASE", f"sqlite:///{app.instance_path}/ladder.db"),
    settings=db_settings,
    season_config_dir=app.instance_path,
    logger=logger,
)

# Initialize a background task pool
sequential_background_task_executor = ThreadPoolExecutor(1)


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
                ("Home", "home"),
                ("Ladder", "ladder"),
                ("High Score", "highscore"),
                ("History", "history"),
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

    return ret


def _get_seasons_menu(season_group: str = "seasons", **args) -> dict:
    cur_endpoint, cur_mod, cur_period = _get_request_params()
    _seasons: dict[Season] = {s.id: s for s in MainDB.get_seasons()[cur_mod].values() if s.group == season_group}
    period_options = []
    for _season in _seasons.values():
        period_options.append((_season.title, _season.id))
    ret = [
        {
            "caption": caption,
            "url": url_for(cur_endpoint, **args) + _args_url(period=period),
            "active": period == cur_period,
        }
        for caption, period in period_options
    ]
    return ret


@app.route("/")
@app.route("/home")
def home():
    menu = _get_menu()
    ajax_url = url_for("leaderboard_js") + _args_url()
    _, cur_mod, cur_period = _get_request_params()
    season: Season = MainDB.get_seasons()[cur_mod][cur_period]
    return render_template(
        "home.html",
        navbar_menu=menu,
        ajax_url=ajax_url,
        period_info=season.get_info() if cur_period != "all" else None,
        mod_id=cur_mod,
    )


@app.route("/highscore")
def highscore():
    menu = _get_menu()
    cur_endpoint, cur_mod, cur_season = _get_request_params()
    _highscore: [dict] = MainDB.fetch_table("highscore", condition=f"mod_id='{cur_mod}' AND season_group='seasons'")
    banned_player_offset = 0
    for i, row in enumerate(_highscore, start=1):
        row["rank"] = i - banned_player_offset

    return render_template(
        "highscore.html",
        navbar_menu=menu,
        mod_id=cur_mod,
        season_id=cur_season,
        highscore=_highscore,
    )


@app.route("/history")
def history():
    cur_mod = _get_request_params()[1]

    # Human-readable titles for potential season groups
    _season_group_title_lookup = {"seasons": "Seasons", "other": "Other Competitions"}

    _algorithms = {algo["id"]: algo for algo in MainDB.fetch_table(table="algorithm")}

    _season_stats = MainDB.get_all_season_stats(mod=cur_mod)
    for s in _season_stats:
        s["algorithm"] = _algorithms[s["algorithm"]]

    # group season info dictionaries by display group
    _seasons = [
        (_season_group_title_lookup[group_id], [s for s in _season_stats if s["season_group"] == group_id])
        for group_id in _season_group_title_lookup.keys()
    ]

    return render_template(
        "history.html",
        navbar_menu=_get_menu(),
        mod_id=cur_mod,
        seasons=_seasons,
    )


@app.route("/ladder")
def ladder():
    menu = _get_menu()
    seasons_menu = _get_seasons_menu()
    scoreboard_ajax_url = url_for("leaderboard_js") + _args_url()
    latest_games_ajax_url = url_for("latest_games_js") + _args_url()
    _, cur_mod, cur_period = _get_request_params()
    season: Season = MainDB.get_seasons()[cur_mod][cur_period]

    season_info = season.get_info()
    if season_info is not None:
        season_info["algorithm"] = MainDB.fetch_table("algorithm", condition=f"id='{season.algorithm}'")[0]

    return render_template(
        "ladder.html",
        navbar_menu=menu,
        seasons_menu=seasons_menu,
        period_info=season_info,
        mod_id=cur_mod,
        scoreboard_ajax_url=scoreboard_ajax_url,
        games_ajax_url=latest_games_ajax_url,
        season_stats=MainDB.get_season_stats(mod=cur_mod, season_id=season.id),
        faction_stats=_get_global_faction_stats(MainDB, mod=cur_mod),
        map_stats=_get_global_map_stats(MainDB, season),
        activity_stats=_get_activity_stats(MainDB, season),
    )


@app.route("/player/<int:profile_id>")
def player(profile_id):
    _, cur_mod, cur_period = _get_request_params()
    show_career_statistics = request.args.get("show_career_statistics", False) in ["True", "true"]
    current: Season = MainDB.get_seasons()[cur_mod][cur_period]

    _menu = _get_menu(profile_id=profile_id)

    _now = datetime.datetime.now

    if not MainDB.check_player_active_mod(mod=cur_mod, profile_id=profile_id):
        # ToDo: display general player info even if not active in this mod
        return render_template("noplayer.html", navbar_menu=_menu, profile_id=profile_id, mod_id=cur_mod)
    else:
        _start = _now()
        _player = MainDB.get_player_info(profile_id, mod_id=cur_mod)
        app.logger.debug(f"Profile load time, get_player_info: {_now() - _start}")

    active_in_current_season = MainDB.check_player_active_season(
        mod=cur_mod, season_id=cur_period, profile_id=profile_id
    )
    _player["current_season"] = active_in_current_season

    # Collect player history information
    _start = _now()
    _player["season_history"] = list(MainDB.get_player_season_history(mod=cur_mod, profile_id=profile_id).values())
    app.logger.debug(f"Profile load time, get_player_season_history: {_now() - _start}")

    _start = _now()
    _player["other_seasons"] = list(
        MainDB.get_player_season_history(mod=cur_mod, profile_id=profile_id, season_group="other").values()
    )
    app.logger.debug(f"Profile load time, get_player_season_history/other_seasons: {_now() - _start}")

    if not active_in_current_season:
        # We will display career statistics
        show_career_statistics = True

    _start = _now()
    _cur_season = None if show_career_statistics else cur_period

    if show_career_statistics:
        # Take final rating at the end of each season, sort chronologically by season end date
        rating_history = sorted(
            [
                # 3-tuple: end_date, rating, season title
                (s["season"]["end"], s["rating"], s["season"]["title"])
                for s in _player["season_history"]
            ],
            key=lambda x: x[0],
        )
        rating_stats = dict(
            # use season title as label
            labels=list(map(lambda x: x[2], rating_history)),
            data=list(map(lambda x: x[1], rating_history)),
        )
    else:
        # get current season's ratings over time
        rating_stats = _get_player_ratings(MainDB, mod=cur_mod, season_id=_cur_season, profile_id=profile_id)

    app.logger.debug(f"Profile load time, _get_player_ratings: {_now() - _start}")

    _start = _now()
    opponent_stats = MainDB.get_player_opponent_statistics(mod=cur_mod, player_id=profile_id, season_id=_cur_season)
    app.logger.debug(f"Opponent stats load time, MainDB.get_player_opponent_statistics: {_now() - _start}")

    _start = _now()
    faction_stats = _get_player_faction_stats(MainDB, mod=cur_mod, profile_id=profile_id, season_id=_cur_season)
    app.logger.debug(f"Profile load time, _get_player_faction_stats: {_now() - _start}")

    _start = _now()
    map_stats = _get_player_map_stats(MainDB, mod=cur_mod, profile_id=profile_id, season_id=_cur_season)
    app.logger.debug(f"Profile load time, _get_player_map_stats: {_now() - _start}")

    ajax_url = url_for("player_games_js", profile_id=profile_id) + _args_url(
        show_career_statistics=show_career_statistics
    )

    return render_template(
        "player.html",
        navbar_menu=_menu,
        player=_player,
        ajax_url=ajax_url,
        rating_stats=rating_stats,
        opponent_stats=opponent_stats,
        faction_stats=faction_stats,
        map_stats=map_stats,
        mod_id=cur_mod,
        season_info=current.get_info(),
        show_career_statistics=show_career_statistics,
    )


@app.route("/about")
@app.route("/info")
def info():
    menu = _get_menu()
    _, cur_mod, cur_period = _get_request_params()
    season = MainDB.get_seasons()[cur_mod]["2m"]
    return render_template(
        "info.html",
        navbar_menu=menu,
        period_info=season.get_info(),
        mod=mods[cur_mod],
        mod_id=cur_mod,
    )


@app.route("/leaderboard-js")
@app.route("/api/leaderboard")
def leaderboard_js():
    # requires HTTP request parameters "mod" and "period"
    _, mod, season_id = _get_request_params()
    data = MainDB.get_leaderboard(mod=mod, season_id=season_id)

    rows = []
    for row in data:
        rows.append(
            dict(
                row_id=row["rank"],
                player=dict(
                    name=row["profile_name"],
                    url=url_for("player", profile_id=row["profile_id"]) + _args_url(),
                    avatar_url=row["avatar_url"],
                ),
                rating=dict(
                    value=row["rating"],
                    diff=row["difference"],
                ),
                played=row["wins"] + row["losses"],
                wins=row["wins"],
                losses=row["losses"],
                winrate=row["wins"] / (row["wins"] + row["losses"]) * 100,
                rank={
                    "rank": row["rank"],
                    "is_official": cast_boolean(row["eligible"]),
                    "comment": row["comment"],
                },
            )
        )

    return jsonify(rows)


@app.route("/latest-js")
@app.route("/api/games")
def latest_games_js():
    _endpoint, cur_mod, _season_id = _get_request_params()
    app.logger.debug(f"Requested {_endpoint}, args: {request.args}.")
    if "period" not in request.args:
        app.logger.debug(f"Season ID not specified, trying to infer requested set of games.")
        if "start" in request.args:
            start_date = datetime.date.fromisoformat(request.args["start"])
            if "end" in request.args:
                end_date = datetime.date.fromisoformat(request.args["end"]) + datetime.timedelta(days=1)
            else:
                end_date = datetime.date.today() + datetime.timedelta(days=1)
            app.logger.debug(f"Collecting games played between {start_date} and {end_date}.")
            condition = (
                f"`mod`='{cur_mod}' AND end_time>='{start_date.isoformat()}' "
                f"AND end_time<='{end_date.isoformat()}' ORDER BY end_time DESC"
            )
        else:
            # period/season has not been explicitly specified,
            # we imply that all games from past 14 days shall be returned
            end_date = datetime.date.today() - datetime.timedelta(days=14)
            app.logger.debug(f"Collecting last 14 days' games.")
            condition = f"`mod`='{cur_mod}' AND end_time>='{end_date.isoformat()}' ORDER BY end_time DESC"
    else:
        condition = f"`mod`='{cur_mod}' AND season_id='{_season_id}' ORDER BY end_time DESC"

    matches = MainDB.fetch_table("SeasonGames", condition=condition)

    games = {}
    for match in matches:
        p0_banned = match["p0_banned"] == "True"
        p1_banned = match["p1_banned"] == "True"
        game = dict(
            replay=dict(
                hash=match["hash"],
                url=url_for("replay", replay_hash=match["hash"]) + _args_url(),
                supports_analysis=mods[cur_mod].get("supports_analysis", False),
            )
            if not (p0_banned or p1_banned)
            else None,
            date=match["end_time"],
            duration=match["duration"],
            map=_stripped_map_name(match["map_title"]),
            p0=dict(
                name=escape(match["p0_name"]),
                url=url_for("player", profile_id=match["profile_id0"]) + _args_url(),
                diff=match["diff0"],
            )
            if not p0_banned
            else None,
            p1=dict(
                name=escape(match["p1_name"]),
                url=url_for("player", profile_id=match["profile_id1"]) + _args_url(),
                diff=match["diff1"],
            )
            if not p1_banned
            else None,
        )
        # use a dictionary instead of list to filter out potential duplicate entries (due to games being recorded into
        # multiple seasons)
        games[match["hash"]] = game

    games_list = list(games.values())
    return jsonify(games_list)


@app.route("/replay/<replay_hash>")
@app.route("/api/games/<replay_hash>")
def replay(replay_hash):
    fullpath = MainDB.get_replay_filename(hash=replay_hash)
    return send_file(fullpath, as_attachment=True)


@app.route("/api/games/<replay_hash>", methods=["DELETE"])
@api_key_authn(keys=[app.config.get("LADDER_API_KEY")])
def delete_replay(replay_hash):
    res = api_system.delete_replay(database=MainDB, hash=replay_hash)
    if res:
        app.logger.info(f'Deleted replay {res["hash"]}')
        return jsonify({"deleted": res["hash"]})
    else:
        app.logger.info(f"Could not delete replay {replay_hash}, not found in database")
        return Response(status=422)


@app.route("/player-games-js/<int:profile_id>")
@app.route("/api/player/<int:profile_id>/games")
def player_games_js(profile_id):
    _, cur_mod, cur_season = _get_request_params()
    show_career_statistics = request.args.get("show_career_statistics", False) in ["True", "true"]
    if show_career_statistics:
        season_condition = ""
        table = "SeasonGames"
    else:
        season_condition = f"AND season_id='{cur_season}' "
        table = "SeasonGames"

    condition = (
        f"`mod`='{cur_mod}' {season_condition}"
        f"AND (profile_id0='{profile_id}' OR profile_id1='{profile_id}') "
        f"ORDER BY end_time DESC"
    )
    player_games = MainDB.fetch_table(table, condition=condition, distinct=True)
    games = []
    for match in player_games:
        if match["profile_id0"] == profile_id:
            diff = match["diff0"]
            opponent = escape(match["p1_name"])
            opponent_id = match["profile_id1"]
            opponent_banned = cast_boolean(match["p1_banned"])
            banned = cast_boolean(match["p0_banned"])
            outcome = "Won"
        else:
            diff = match["diff1"]
            opponent = escape(match["p0_name"])
            opponent_id = match["profile_id0"]
            opponent_banned = cast_boolean(match["p0_banned"])
            banned = cast_boolean(match["p1_banned"])
            outcome = "Lost"
        if show_career_statistics:
            # remove rating points
            diff = None
        if not (banned or opponent_banned):
            game = dict(
                date=match["end_time"],
                opponent=dict(
                    name=opponent,
                    url=url_for("player", profile_id=opponent_id) + _args_url(),
                ),
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
                ),
            )
            games.append(game)
        if show_career_statistics:
            # deduplicate
            games_strings = [json.dumps(g) for g in games]
            unique_game_strings = list(set(games_strings))
            games = [json.loads(gstr) for gstr in unique_game_strings]
    return jsonify(games)


@app.route("/api/system/refresh", methods=["POST"])
@api_key_authn(keys=[app.config.get("LADDER_API_KEY")])
def system_refresh():
    app.logger.info("Initializing system refresh")

    request_payload: Union[dict, None] = request.get_json() if request.is_json else None
    app.logger.debug(f"JSON payload: {request_payload}")

    skip_inactive = True
    do_parse_replays = True
    max_file_age_days = 7

    if request_payload is not None:
        skip_inactive = cast_boolean(request_payload.get("skip_inactive", True))
        do_parse_replays = cast_boolean(request_payload.get("parse_replays", True))
        max_file_age_days = int(request_payload.get("max_file_age_days", 7))

    app.logger.debug(f"Param skip_inactive: {skip_inactive}")
    app.logger.debug(f"Param do_parse_replays: {do_parse_replays}")
    app.logger.debug(f"Param max_file_age_days: {max_file_age_days}")

    seasons = MainDB.get_seasons()

    for mod in seasons.keys():
        if do_parse_replays:
            parsing_result = parse_replays(
                mod_id=mod, skip_inactive=skip_inactive, max_file_age_days=max_file_age_days
            ).json
            app.logger.debug(
                f"Parsed {parsing_result['replays_parsed']} replays "
                f"for mod {mod} in {parsing_result['processing_time']} "
            )
            if parsing_result["replays_parsed"] < 1:
                # Don't do any further processing if no new replays have been parsed
                app.logger.debug(f"Skipping update procedures for mod {mod}")
                continue

        # Try and rotate the currently active period
        # (i.e. create a new running season if the last one reached its designated end date)
        rotate_season(mod_id=mod)

        for season_id, season in seasons[mod].items():
            if season_id:
                if skip_inactive and not season.active:
                    continue
                update_ranking(mod_id=mod, season_id=season_id)
    # ToDo: useful return
    return jsonify(True)


@app.route("/api/system/update_rankings", methods=["POST"])
@api_key_authn(keys=[app.config.get("LADDER_API_KEY")])
def update_rankings():
    """Trigger a database update for all available seasons.

    Will execute all the required updates as background tasks;
    see update_ranking() method for further details.
    """
    app.logger.info("Initializing full ranking update")
    seasons = MainDB.get_seasons()
    for mod in seasons.keys():
        for season_id, season in seasons[mod].items():
            if season_id:
                update_ranking(mod_id=mod, season_id=season_id)
    return jsonify("Scheduled database update for all seasons.")


@app.route("/api/<mod_id>/parse_replays", methods=["POST"])
@api_key_authn(keys=[app.config.get("LADDER_API_KEY")])
def parse_replays(mod_id, skip_inactive: bool = True, max_file_age_days: Optional[int] = None):
    app.logger.info(f"Parsing replays for mod {mod_id}")
    seasons = MainDB.get_seasons()
    parsed_folders = {}
    result = {"replays_parsed": 0, "processing_time": datetime.timedelta(0)}
    for mod in seasons.keys():
        if mod != mod_id:
            continue
        parsed_folders[mod] = []
        for season_id, season in seasons[mod].items():
            if skip_inactive and not season.active:
                continue
            if season.replay_path not in parsed_folders[season.mod]:
                app.logger.info(f"Parsing replays from {season.replay_path} for mod {season.mod}")
                parsing_result, _ = api_system.parse_replays(
                    database=MainDB,
                    mod=season.mod,
                    replay_directory=season.replay_path,
                    max_file_modified_days=max_file_age_days,
                    skip_known_files=True,
                    logger=logger,
                )
                parsed_folders[season.mod].append(season.replay_path)
                result["replays_parsed"] += parsing_result["replays_parsed"]
                result["processing_time"] += parsing_result["processing_time"]

    app.logger.info(
        f"Done parsing replay files, {result['replays_parsed']} new replays parsed " f"in {result['processing_time']}"
    )
    result["processing_time"] = str(result["processing_time"])
    return jsonify(result)


@app.route("/api/<mod_id>/<season_id>/update", methods=["POST"])
@api_key_authn(keys=[app.config.get("LADDER_API_KEY")])
def update_ranking(mod_id, season_id):
    """Update database for a specific season.

    Refreshes player rating and ranking; updates highscores table
    and player_season_history table.

    Task will be executed in sequence as a background thread.
    """
    season = MainDB.get_seasons()[mod_id][season_id]

    def _background_task():
        app.logger.info(f"Updating ratings for {mod_id}/{season_id}")
        api_system.update_season_ratings(database=MainDB, season=season)
        app.logger.info(f"Updating rankings for {mod_id}/{season_id}")
        api_system.update_season_ranking(database=MainDB, season=season)
        app.logger.info(f"Updating highscore for {mod_id}/{season.group}")
        api_system.update_highscore(database=MainDB, mod_id=season.mod, season_group=season.group)
        app.logger.info(f"Updating history table for {mod_id}/{season_id}")
        MainDB.update_season_history(mod_id=mod_id, season_id=season_id)
        app.logger.info(f"Updating player_season_history table for {mod_id}/{season.id}")
        MainDB.update_player_season_history(mod_id=mod_id, season_id=season.id, season_group=season.group)
        app.logger.info(f"Completed update of ratings and subsequent information for {mod_id}/{season_id}.")

    if season:
        sequential_background_task_executor.submit(_background_task)
        app.logger.info(f"Started update of ratings and subsequent information for {mod_id}/{season_id}.")
        return jsonify(f"Scheduled database update for {mod_id}/{season_id}")
    else:
        msg = f"No such season: {mod_id}/{season_id}"
        app.logger.warning(msg)
        return msg, 400


@app.route("/api/rotate_current_season", methods=["POST"])
@api_key_authn(keys=[app.config.get("LADDER_API_KEY")])
def rotate_season(mod_id: Optional[str] = None):
    app.logger.info(f"Initializing season rotation.")
    api_system.rotate_current_2m_season(db=MainDB, mod=mod_id)
    MainDB.update_season_history(mod_id=mod_id)
    # ToDo: useful return
    return jsonify(True)


@app.route("/api/system/update_player_profiles", methods=["POST"])
@api_key_authn(keys=[app.config.get("LADDER_API_KEY")])
def update_player_profiles():
    """Query and update internal profile information from OpenRA Forum API for all known user accounts"""
    return api_system.update_player_profiles(database=MainDB)
