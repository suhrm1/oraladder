#
# Copyright (C) 2020
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
import os
import os.path as op
import logging
from typing import Optional
from urllib.request import urlopen

from . import miniyaml, replay
from .replay import GamePlayerInfo


def _update_account_cache(accounts_db: dict, player: GamePlayerInfo):
    """
    Query OpenRA account service to get information on the player
    """

    fingerprint = player.fingerprint

    if fingerprint in accounts_db:  # already in cache
        return accounts_db[fingerprint] is not None

    logging.info(f"Querying {player.display_name} with fingerprint {fingerprint}...")
    player_url = f"https://forum.openra.net/openra/info/{fingerprint}"

    try:
        player_yaml = urlopen(player_url).read()
    except Exception:
        logging.error(f"Failed to fetch player info with {fingerprint=}")
        accounts_db[fingerprint] = None
        return False

    if not player_yaml:
        logging.error("Player info is empty")
        accounts_db[fingerprint] = None
        return False

    player_info = miniyaml.load(player_yaml)
    if "Error" in player_info:
        logging.error(player_info["Error"])
        accounts_db[fingerprint] = None
        return False

    profile_fp = player_info["Player"]["Fingerprint"]
    if profile_fp != fingerprint:
        logging.error(f"Player fingerprint doesn't match: {profile_fp} != {fingerprint}")
        accounts_db[fingerprint] = None
        return False

    profile_id = int(player_info["Player"]["ProfileID"])
    profile_name = player_info["Player"]["ProfileName"]
    avatar = player_info["Player"]["Avatar"]
    avatar_url = avatar["Src"] if avatar else ""
    accounts_db[fingerprint] = (profile_id, profile_name, avatar_url)

    logging.info(f"{fingerprint}: {profile_name=} {profile_id=}")
    return True


def _parse_replay(results, accounts_db, filename):
    if not filename.endswith(".orarep"):
        return
    try:
        result = replay.get_result(filename)
    except Exception as e:
        logging.error(f"{op.basename(filename)}: {e}")
        return
    if _update_account_cache(accounts_db, result.player0) and _update_account_cache(accounts_db, result.player1):
        results.append(result)
        logging.info(f"{op.basename(filename)}: recorded")


def _filter_period(results, period_dict: Optional[dict]):
    if period_dict is None:
        return results
    start = period_dict["start"]
    end = period_dict["end"]
    return [r for r in results if (start <= r.end_time.date() <= end)]


def get_results(accounts_db, replays, period_dict: Optional[dict] = None):
    results = []
    for filename in replays:
        if op.isdir(filename):
            for root, dirs, files in os.walk(filename):
                for name in files:
                    _parse_replay(results, accounts_db, op.join(root, name))
        else:
            _parse_replay(results, accounts_db, filename)
    results = _filter_period(results, period_dict)
    return sorted(results, key=lambda r: r.end_time)


_banned_profile_re = re.compile(r"^\d+")


def get_profile_ids(bans_file):
    with open(bans_file) as banf:
        return [int(_banned_profile_re.search(line).group()) for line in banf]
