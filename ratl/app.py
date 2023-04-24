import os
from flask import Flask, jsonify, render_template, send_file, redirect
from .config import config
from .replays import parse_replays, filter_valid_teamgames, game_info
from .cache import load_json_cache, save_json_cache

app = Flask(__name__)

if not config["replay_folder"]:
    config["replay_folder"] = os.path.join(app.instance_path, "replays")
    if not os.path.exists(config["replay_folder"]):
        os.makedirs(config["replay_folder"], exist_ok=True)

if not config["config_folder"]:
    config["config_folder"] = os.path.join(app.instance_path)


def _prepare_game_list() -> list:
    """Parses replays, fetches player account data (if necessary), and filters out valid games

    Only games between officially registered teams will be kept. All replays in the replay folder (and subfolder)
    will be parsed on every run. Consider caching replay data into a JSON file if this becomes a bottleneck.
    """
    player_db_file = os.path.join(config["config_folder"], "players.json")
    players = load_json_cache(player_db_file)
    replays = parse_replays(config["replay_folder"])
    valid_replays, players = filter_valid_teamgames(replays, config["teams"], fingerprints=players)
    save_json_cache(player_db_file, players)

    game_results = game_info(valid_replays, config["teams"], players)
    # ToDo: sort by endtime
    # game_results.sort(key=lambda game: game["end_time"])
    return game_results


@app.route("/")
@app.route("/games")
def games():
    game_results = _prepare_game_list()
    # replace winning team reference with actual team name
    for game in game_results:
        game["result"] = game["team1"]["name"] if game["result"] == "team1" else game["team2"]["name"]
    return render_template("games.html", games=game_results)


@app.route("/schedule")
def schedule():
    player_names = config["player_names"]
    teams = [
        {"name": teamname, "players": [{"profile_id": pid, "name": player_names[pid]} for pid in players]}
        for teamname, players in config["teams"].items()
    ]
    schedule = config["schedule"]
    # ToDo: determine which games have been completed...
    return render_template("schedule.html", teams=teams, schedule=schedule)


@app.route("/replay/<replay_hash>")
def replay(replay_hash):
    games = _prepare_game_list()
    for g in games:
        if g["replay_id"] == replay_hash:
            fullpath = g["filename"]
            original_filename = os.path.basename(fullpath)
            attachment_filename = original_filename
            return send_file(fullpath, as_attachment=True, download_name=attachment_filename)
    return redirect("/")


@app.route("/api/v1/games")
def api_games():
    return jsonify(_prepare_game_list())
