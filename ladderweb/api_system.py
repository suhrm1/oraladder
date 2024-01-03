import calendar
import copy
import datetime
import logging
import os
import shutil
from datetime import date
from hashlib import sha256
from operator import itemgetter
from typing import Dict, Tuple, Optional
from logging import Logger, getLogger

from laddertools.model import PlayerLookup
from laddertools.rankings import ranking_systems
from laddertools.rankings.abc import RankingBase
from laddertools.replay import get_result, GameResult, GamePlayerInfo
from laddertools.utils import _update_account_cache, get_profile_ids as get_banned_profiles
from ladderweb.model.seasons import Season
from ladderweb.model import LadderDatabase
from ladderweb.ranking_criteria import check_eligible


def _accounts_db(database: LadderDatabase) -> Dict[str, Tuple[str, str, str]]:
    """Produce a dict of fingerprint: (profile_id, profile_name, avatar_url) for every OpenRA Forum account in database"""
    return {
        account["fingerprint"]: (account["profile_id"], account["profile_name"], account["avatar_url"])
        for account in database.fetch_table("accounts")
    }


def update_highscore(database: LadderDatabase, mod_id: str, season_group: str = "seasons"):
    highscore = database.get_highscore(mod_id=mod_id, group_id=season_group)
    for row in highscore:
        row.update({"mod_id": mod_id, "season_group": season_group})
    with database.engine.begin() as txn:
        delete_sql = f"DELETE FROM highscore WHERE mod_id='{mod_id}' AND season_group='{season_group}';"
        database.exec(delete_sql, transaction=txn)
        database.batch_insert(table="highscore", batch=highscore, transaction=txn)


def parse_replays(
    database: LadderDatabase,
    mod: str,
    replay_directory: str,
    skip_known_files: bool = True,
    max_file_modified_days: Optional[int] = None,
    known_accounts: Dict = {},
    logger: Logger = getLogger(),
):
    logger.debug(f"Parsing replay files for mod {mod} from folder {replay_directory}")
    # prepare a timer
    _now = datetime.datetime.now
    _start_time = _now()
    recursion_games_count = 0

    # create a dict of known player accounts as required by the laddertools._update_account_cache() method
    if known_accounts is None:
        known_accounts = _accounts_db(database)

    if not os.path.exists(replay_directory):
        logger.warning(f"Designated replay path {replay_directory} does not exist.")
        return {
            "replays_parsed": 0,
            "processing_time": datetime.timedelta(0),
        }, known_accounts

    for f in os.listdir(replay_directory):
        if os.path.isdir(replay_directory + f):
            subfolder = replay_directory + f + "/"
            logger.debug(f"Subfolder {f}, entering recursion")
            recursion_result, known_accounts = parse_replays(
                database=database,
                mod=mod,
                replay_directory=subfolder,
                skip_known_files=skip_known_files,
                max_file_modified_days=max_file_modified_days,
                known_accounts=known_accounts,
            )
            recursion_games_count += recursion_result["replays_parsed"]

    if skip_known_files:
        known_files = [f["filename"] for f in database.fetch_table("game")]
        broken_files = [row["filename"] for row in database.fetch_table("broken_replays")]
        known_files += broken_files
    else:
        known_files = []

    replays: {str} = {replay_directory + f for f in os.listdir(replay_directory) if f.endswith(".orarep")}
    replays = list(replays - set(known_files))

    if max_file_modified_days is not None:
        if max_file_modified_days >= 0:
            logger.debug(
                f"Excluding replay files older than {max_file_modified_days} days (based on OS file modified time)"
            )
            today = date.today()
            for path in replays:
                mdate = date.fromtimestamp(os.path.getmtime(path))
                if (today - mdate).days >= max_file_modified_days:
                    replays.remove(path)
                    logger.debug(f"Skipping {path} (modified date: {mdate})")

    if len(replays) < 1:
        # nothing to do
        return {"replays_parsed": 0 + recursion_games_count, "processing_time": _now() - _start_time}, known_accounts

    broken_replays = []

    results: [GameResult] = []
    for replay in replays:
        # parse replay into laddertools.GameResult object
        try:
            result: GameResult = get_result(replay)
            if _update_account_cache(known_accounts, result.player0) and _update_account_cache(
                known_accounts, result.player1
            ):
                results.append(result)
        except Exception as e:
            logger.error(f"Error parsing replay file {replay}")
            yesterday = today - datetime.timedelta(days=1)
            if today.isoformat() not in replay and yesterday.isoformat() not in replay:
                # replay may still be in progress, only block it from-reparsing if it does not contain recent date
                broken_replays.append({"filename": replay, "parse_date": datetime.date.today()})

    if len(broken_replays):
        database.batch_upsert(table="broken_replays", batch=broken_replays, primary_key="filename")

    bans_file = database.get_config_value("bans_file")
    if bans_file is not None:
        banned_profiles = get_banned_profiles(bans_file)
    else:
        banned_profiles = []

    # Update account database
    accounts = [
        {
            "fingerprint": fingerprint,
            "profile_id": account[0],
            "profile_name": account[1].replace("'", "").strip(),
            "avatar_url": account[2],
            "banned": int(account[0] in banned_profiles),
        }
        for fingerprint, account in known_accounts.items()
        if account is not None
    ]
    database.batch_upsert("accounts", batch=accounts, primary_key="fingerprint")

    # Update game results
    games = [
        {
            "hash": sha256(game.filename.encode()).hexdigest(),
            "mod": mod,
            "start_time": game.start_time,
            "end_time": game.end_time,
            "filename": game.filename,
            "profile_id0": known_accounts[game.player0.fingerprint][0],
            "profile_id1": known_accounts[game.player1.fingerprint][0],
            "faction_0": game.player0.faction,
            "faction_1": game.player1.faction,
            "selected_faction_0": game.player0.selected_faction,
            "selected_faction_1": game.player1.selected_faction,
            "map_uid": game.map_uid,
            "map_title": game.map_title,
        }
        for game in results
    ]
    database.batch_upsert(table="game", batch=games, primary_key="hash")

    return {
        "replays_parsed": (len(games) + recursion_games_count),
        "processing_time": _now() - _start_time,
    }, known_accounts


def update_season_ratings(database: LadderDatabase, season: Season):
    algorithm: RankingBase = ranking_systems[season.algorithm]()
    accounts = _accounts_db(database)
    banned_profiles = database.get_banned_profile_ids()

    player_fingerprints = {}
    for fingerprint, account in accounts.items():
        player_fingerprints[account[0]] = fingerprint

    player_lookup = PlayerLookup(accounts, algorithm)

    end_time = season.end + datetime.timedelta(days=1)
    results = database.get_games(mod_id=season.mod, start=season.start, end=end_time)

    game_results: [GameResult] = []
    for result in results:
        player_0_id = result["profile_id0"]
        player_1_id = result["profile_id1"]
        if not ((player_0_id in banned_profiles) or (player_1_id in banned_profiles)):
            result.update(
                {
                    "player0": GamePlayerInfo(
                        fingerprint=player_fingerprints[player_0_id],
                        display_name=player_lookup[player_0_id].name,
                        faction=result["faction_0"],
                        selected_faction=result["selected_faction_0"],
                    ),
                    "player1": GamePlayerInfo(
                        fingerprint=player_fingerprints[player_1_id],
                        display_name=player_lookup[player_1_id].name,
                        faction=result["faction_1"],
                        selected_faction=result["selected_faction_1"],
                    ),
                }
            )
            g = GameResult(**result)
            game_results.append(g)

    _, outcomes = algorithm.compute_ratings_from_series_of_games(game_results, player_lookup)

    ratings = []
    for outcome in outcomes:
        rating0 = {
            "replay_hash": outcome._hash,
            "season_id": season.id,
            "mod": season.mod,
            "profile_id": outcome._p0_profile_id,
            "value": outcome._p0_rating1.display_value,
            "difference": outcome._p0_rating1.display_value - outcome._p0_rating0.display_value,
        }
        ratings.append(rating0)
        rating1 = copy.deepcopy(rating0)
        rating1.update(
            {
                "profile_id": outcome._p1_profile_id,
                "value": outcome._p1_rating1.display_value,
                "difference": outcome._p1_rating1.display_value - outcome._p1_rating0.display_value,
            }
        )
        ratings.append(rating1)

    database.exec(f"DELETE FROM rating WHERE `mod`='{season.mod}' and season_id='{season.id}';")
    database.batch_insert(table="rating", batch=ratings)

    return True


def update_season_ranking(database: LadderDatabase, season: Season):
    query = f"SELECT DISTINCT r.profile_id FROM rating r WHERE r.season_id='{season.id}' AND r.`mod`='{season.mod}';"
    players = [r[0] for r in database.exec(query, fetch=True)]
    banned_profiles = database.get_banned_profile_ids()
    end_time = season.end + datetime.timedelta(days=1)
    season_games = database.get_games(mod_id=season.mod, start=season.start, end=end_time, order_by="end_time DESC")
    player_wins = {p_id: 0 for p_id in players}
    player_losses = copy.deepcopy(player_wins)
    player_last_game = {}
    for game in season_games:
        winner_id, loser_id = game["profile_id0"], game["profile_id1"]
        if not (winner_id in banned_profiles or loser_id in banned_profiles):
            player_wins[winner_id] += 1
            player_losses[loser_id] += 1
            if winner_id not in player_last_game.keys():
                player_last_game[winner_id] = game["hash"]
            if loser_id not in player_last_game.keys():
                player_last_game[loser_id] = game["hash"]

    columns = ["profile_id", "season_id", "eligible", "wins", "losses", "rating", "rank"]
    batch = []
    for profile_id in players:
        last_game_hash = player_last_game[profile_id]
        rating, diff = database.exec(
            f"SELECT value, difference FROM rating WHERE replay_hash='{last_game_hash}' "
            f"AND profile_id='{profile_id}' AND season_id='{season.id}' AND `mod`='{season.mod}'",
            fetch=True,
        )[0]

        if season.algorithm == "openskill":
            eligible, explanation = check_eligible(db=database, season=season, profile_id=profile_id)
        else:
            eligible, explanation = True, None

        batch.append(
            {
                "profile_id": profile_id,
                "season_id": season.id,
                "mod": season.mod,
                "eligible": 1 if eligible else 0,
                "comment": explanation,
                "wins": player_wins[profile_id],
                "losses": player_losses[profile_id],
                "rating": rating,
                "difference": diff,
                "rank": None,
            }
        )

    # Sort by highest ratings
    batch = sorted(batch, key=itemgetter("rating"), reverse=True)

    # If season has reached its designated end, mark it as inactive
    if season.end is not None:
        if (season.end - date.today()).days < 0 and season.active:
            # update status
            season.active = 0
            database.exec(f"UPDATE season SET active={season.active} WHERE `mod`='{season.mod}' AND id='{season.id}';")
            logging.debug(
                f"Updated seasons {season.mod}/{season.id} status, set inactive based on end date {season.end}"
            )

    # Calculate official ranking (i.e. skipping players considered not eligible for official ranking)
    unranked = 0
    for rank, row in enumerate(batch, 1):
        if season.active:
            # Mark preliminary ranking for ongoing seasons
            row.update({"rank": rank})
        else:
            # Strictly enforce ranking criteria for completed seasons
            if row["eligible"]:
                row.update({"rank": rank - unranked})
            else:
                unranked += 1

    with database.engine.begin() as txn:
        database.exec(f"DELETE FROM ranking WHERE season_id='{season.id}' AND `mod`='{season.mod}'", transaction=txn)
        database.batch_insert(table="ranking", batch=batch, transaction=txn)


def rotate_current_2m_season(db: LadderDatabase, mod: Optional[str] = None):
    seasons = db.get_seasons()
    if mod is not None:
        mods = [mod]
    else:
        mods = list(seasons.keys())
    today = datetime.date.today()
    for mod_id in mods:
        old_current_season: Season = seasons[mod_id]["2m"]
        # if season end date has been reached
        if (today - old_current_season.end).days > 0:
            new_current_season = copy.deepcopy(old_current_season)

            prev_end_date = old_current_season.start - datetime.timedelta(days=1)
            for _season in seasons[mod_id].values():
                if _season.group != "seasons":
                    continue
                if _season.end == prev_end_date:
                    last_archived_season = _season
                    break

            update_season_name, update_season_nr = last_archived_season.title.split(sep=" ")
            update_season_nr = str(int(update_season_nr) + 1)
            update_season_name += " " + update_season_nr
            update_season_id = "s" + "{0:0>2}".format(update_season_nr)
            old_current_season.id = update_season_id
            old_current_season.title = update_season_name

            new_current_season.start = old_current_season.end + datetime.timedelta(days=1)
            new_end_year, new_end_month = new_current_season.start.year, new_current_season.start.month + 1
            new_end_day = calendar.monthrange(
                year=new_current_season.start.year, month=new_current_season.start.month + 1
            )[1]
            new_current_season.end = datetime.date(year=new_end_year, month=new_end_month, day=new_end_day)
            new_current_season.active = True

            old_season_dict = old_current_season.dict()
            db.update_row_condition(
                table="season",
                values=list(old_season_dict.values()),
                columns=list(old_season_dict.keys()),
                condition=f"`mod`='{mod_id}' AND id='2m'",
            )

            db.batch_insert(table="season", batch=[new_current_season.dict()])

            update_season_ratings(db, season=old_current_season)
            update_season_ranking(db, season=old_current_season)
            update_season_ratings(db, season=new_current_season)
            update_season_ranking(db, season=new_current_season)


def update_player_profiles(database: LadderDatabase):
    _start = datetime.datetime.now()
    accounts_dict = _accounts_db(database=database)
    updated_accounts = {}
    updated_profiles = []
    errors = []

    for fingerprint, account_triple in accounts_dict.items():
        logging.debug(
            f"Updating player {account_triple[1]} (profile_id {account_triple[0]}, fingerprint {fingerprint})"
        )
        player = GamePlayerInfo(
            fingerprint=fingerprint, display_name=account_triple[1], faction="", selected_faction=""
        )
        _update_account_cache(updated_accounts, player)
        if updated_accounts[fingerprint] is not None and updated_accounts[fingerprint][2] != account_triple[2]:
            # profile_id and profile_name should not change
            update_sql = (
                f"UPDATE accounts "
                f"SET avatar_url='{updated_accounts[fingerprint][2]}' "
                f"WHERE fingerprint='{fingerprint}';"
            )
            database.exec(update_sql)
            updated_profiles.append(updated_accounts[fingerprint])
            logging.debug(f"Updated player account {updated_accounts[fingerprint]}")
        else:
            errors.append((fingerprint, player.display_name))

    updated_profiles = set(updated_profiles)
    errors = set(errors)
    processing_time = datetime.datetime.now() - _start

    return {
        "updated_profiles": list(updated_profiles),
        "update_count": len(updated_profiles),
        "processing_time": str(processing_time),
        "error_count": len(errors),
        "query_count": len(accounts_dict),
    }


def delete_replay(database: LadderDatabase, hash: str):
    """Delete a replay from database and move the file to a designated archive directory

    Returns game info on success, False otherwise
    """
    # validate replay exists
    sql = f"SELECT * FROM game WHERE hash='{hash}';"
    res = database.exec(sql, fetch=True)
    if res:
        game = res[0]._asdict()
        deleted_replay_folder = database.get_config_value("deleted_replay_folder")
        os.makedirs(deleted_replay_folder, exist_ok=True)
        moved_file = shutil.copy(src=game["filename"], dst=deleted_replay_folder)
        os.remove(game["filename"])
        logging.debug(f"Moved deleted replay file to {moved_file}")
        sql = f"DELETE FROM game WHERE hash='{hash}';"
        database.exec(sql)
        logging.debug(f"Deleted replay from database: {game}")
        return game
    return False
