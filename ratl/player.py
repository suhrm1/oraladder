import json
import logging
from typing import Union
from urllib.request import urlopen

from laddertools import miniyaml


def get_player_info(fingerprint: str) -> Union[dict, bool]:
    player_url = f"https://forum.openra.net/openra/info/{fingerprint}"

    try:
        player_yaml = urlopen(player_url).read()
        player_info = miniyaml.load(player_yaml)
        return player_info["Player"]
    except Exception:
        logging.error(f"Failed to fetch player info with {fingerprint=}")
        return False
