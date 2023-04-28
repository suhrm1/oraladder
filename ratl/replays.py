import hashlib
import logging
import os
from datetime import datetime
from typing import Tuple

from laddertools.replay import _parse_game_info
from ratl.player import get_player_info


def parse_replays(replay_directory: str, processed_files: list[str] = []) -> Tuple[dict, list]:
    logging.info(f"Parsing replays from {replay_directory}.")
    if not replay_directory.endswith("/"):
        replay_directory += "/"
    replays = {}

    for f in os.listdir(replay_directory):
        if os.path.isdir(replay_directory + f):
            subfolder = replay_directory + f + "/"
            logging.debug(f"Subfolder {f}, entering recursion")
            parsed_replays, parsed_files = parse_replays(replay_directory=subfolder, processed_files=processed_files)
            replays.update(parsed_replays)
            processed_files += parsed_files
        elif f.endswith(".orarep"):
            filename = os.path.join(replay_directory, f)
            if filename in processed_files:
                continue
            replay_id = hashlib.sha1(filename.encode()).hexdigest()
            try:
                with open(filename, "rb") as file:
                    game_data = _parse_game_info(file)
                    game_data["filename"] = filename
                    replays[replay_id] = game_data
                processed_files.append(filename)
            except Exception as e:
                logging.warning(f"Error parsing {filename}: {e}")

    return replays, processed_files


def filter_valid_teamgames(replays: dict, teams: dict, fingerprints: dict = {}) -> (dict, dict):
    valid_replays = {}
    team_tuples = [set(team) for team in teams.values()]
    for replay_id, replay in replays.items():
        t1 = []
        t2 = []
        for key, value in replay.items():
            if str(key).startswith("Player"):
                player_id, fingerprints = lookup_fingerprint(value["Fingerprint"], fingerprints)
                team = int(value["Team"])
                if team == 1:
                    t1.append(player_id)
                elif team == 2:
                    t2.append(player_id)
        if not (len(t1) == len(t2) == 2):
            logging.warning(f"Too many players")
            continue
        elif set(t1) in team_tuples and set(t2) in team_tuples:
            valid_replays[replay_id] = replay
        else:
            logging.warning(f"Invalid team")

    return valid_replays, fingerprints


def lookup_fingerprint(fingerprint: str, known_fingerprints: dict = {}) -> (int, dict):
    if fingerprint not in known_fingerprints:
        player = get_player_info(fingerprint)
        known_fingerprints[fingerprint] = player
    return int(known_fingerprints[fingerprint]["ProfileID"]), known_fingerprints


def game_info(replays: dict, team_config: dict, players: dict) -> list:
    data = []
    for replay_id, replay_data in replays.items():
        logging.info(f"Processing {replay_id}, {replay_data.get('filename')}")
        teams = {1: {}, 2: {}}
        game = {"replay_id": replay_id, "filename": replay_data["filename"]}
        for key, value in replay_data.items():
            if str(key).startswith("Player"):
                fingerprint = value["Fingerprint"]
                player_id, players = lookup_fingerprint(fingerprint, players)
                team_id = int(value["Team"])
                teams[team_id][player_id] = dict(
                    profile_id=player_id,
                    profile_name=players[fingerprint]["ProfileName"],
                    faction=value["FactionName"],
                    faction_random=value["IsRandomFaction"],
                )
                if value["Outcome"] == "Won":
                    game["result"] = "team" + str(team_id)
            elif str(key).startswith("Root"):
                game["start_time"] = datetime.strptime(value["StartTimeUtc"], "%Y-%m-%d %H-%M-%S")
                game["end_time"] = datetime.strptime(value["EndTimeUtc"], "%Y-%m-%d %H-%M-%S")
                game["map"] = value["MapTitle"]
                game["mod"] = value["Mod"]
                game["version"] = value["Version"]
        game["team1"] = {
            "name": _identify_team(team_config, list(teams[1].keys())),
            "players": list(teams[1].values()),
        }
        game["team2"] = {
            "name": _identify_team(team_config, list(teams[2].keys())),
            "players": list(teams[2].values()),
        }
        data.append(game)
    return data


def _identify_team(teams: dict, players: list) -> str:
    p1, p2 = players[0], players[1]
    for team_name, player_ids in teams.items():
        if int(p1) in player_ids and int(p2) in player_ids:
            return team_name
