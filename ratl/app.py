import json
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
    replay_db_file = os.path.join(config["config_folder"], "replays.json")

    cached_replays = load_json_cache(replay_db_file)
    processed_files = [g["filename"] for g in cached_replays.values()] if cached_replays else []
    print(f"processed_files: {processed_files}")
    parsed_replays, _ = parse_replays(config["replay_folder"], processed_files)
    cached_replays.update(parsed_replays)
    save_json_cache(replay_db_file, cached_replays)

    players = load_json_cache(player_db_file)
    valid_replays, players = filter_valid_teamgames(cached_replays, config["teams"], fingerprints=players)
    save_json_cache(player_db_file, players)

    game_results = game_info(valid_replays, config["teams"], players)
    game_results.sort(key=lambda game: game["end_time"], reverse=True)
    return game_results


def _check_scheduled_game_status(schedule: dict):
    games = _prepare_game_list()
    completed_games_per_team = {}
    for g in games:
        t1 = g["team1"]["name"]
        t2 = g["team2"]["name"]
        if t1 in completed_games_per_team.keys():
            if t2 in completed_games_per_team[t1]:
                completed_games_per_team[t1][t2] += 1
            else:
                completed_games_per_team[t1][t2] = 1
        else:
            completed_games_per_team[t1] = {t2: 1}
        if t2 in completed_games_per_team.keys():
            if t1 in completed_games_per_team[t2]:
                completed_games_per_team[t2][t1] += 1
            else:
                completed_games_per_team[t2][t1] = 1
        else:
            completed_games_per_team[t2] = {t1: 1}

    for week in schedule:
        for k, pairing in enumerate(schedule[week]):
            t1 = pairing[1]
            t2 = pairing[2]
            try:
                status = f"{str(completed_games_per_team[t1][t2])}/2 completed"
                row = list(pairing)
                row[3] = status
                schedule[week][k] = tuple(row)
            except KeyError as e:
                pass
    return schedule


@app.route("/")
@app.route("/schedule")
def schedule():
    player_names = config["player_names"]
    teams = [
        {"name": teamname, "players": [{"profile_id": pid, "name": player_names[pid]} for pid in players]}
        for teamname, players in config["teams"].items()
    ]
    schedule = config["schedule"]
    schedule = _check_scheduled_game_status(schedule)

    return render_template("schedule.html", teams=teams, schedule=schedule)


@app.route("/games")
def games():
    game_results = _prepare_game_list()
    # replace winning team reference with actual team name
    for game in game_results:
        game["result"] = game["team1"]["name"] if game["result"] == "team1" else game["team2"]["name"]
    return render_template("games.html", games=game_results)


@app.route("/scoreboards")
def scoreboards():
    player_names = config["player_names"]
    teams = [
        {"name": teamname, "players": [{"profile_id": pid, "name": player_names[pid]} for pid in players]}
        for teamname, players in config["teams"].items()
    ]
    game_results = _prepare_game_list()
    scores = []
    max_games = (len(teams) - 1) * 2
    for team in teams:
        wins = 0
        losses = 0
        for game in game_results:
            winners = game["team1"]["name"] if game["result"] == "team1" else game["team2"]["name"]
            if team["name"] in [game["team1"]["name"], game["team2"]["name"]]:
                if team["name"] == winners:
                    wins += 1
                else:
                    losses += 1
        scores.append(
            {
                "rank": 0,
                "name": f"""{team["name"]} [{team["players"][0]["name"]} & {team["players"][1]["name"]}]""",
                "played": wins + losses,
                "max_matches": max_games,
                "wins": wins,
                "losses": losses,
                "winrate": wins * 100 / (wins + losses) if wins else 0.0,
                "status": "",
            }
        )

    scores.sort(key=lambda x: x["played"], reverse=True)
    scores.sort(key=lambda x: x["winrate"], reverse=True)
    scores.sort(key=lambda x: x["wins"], reverse=True)
    for rank, team in enumerate(scores, 1):
        team.update({"rank": rank})

    return render_template("scoreboards.html", teams=scores)


@app.route("/replay/<replay_hash>")
def replay(replay_hash):
    games = _prepare_game_list()
    for g in games:
        if g["replay_id"] == replay_hash:
            league = config["league_title_short"]
            season = config["season"]
            prefix = f"{league}-S{season:02d}-"

            fullpath = g["filename"]
            original_filename = os.path.basename(fullpath)
            attachment_filename = prefix + original_filename
            return send_file(fullpath, as_attachment=True, download_name=attachment_filename)
    return redirect("/")


@app.route("/api/v1/games")
def api_games():
    return jsonify(_prepare_game_list())
