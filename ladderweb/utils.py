import colorsys
import json
import re
from datetime import timedelta, date
from typing import Any, Optional

import numpy as np

from ladderweb.model import LadderDatabase, Season


def cast_boolean(value: Any) -> bool:
    if value in [1, "1", "true", "True", "y", "Y"]:
        return True
    return False


def _hexc(fc):
    return "#" + "".join("%02X" % int(fc[i] * 255) for i in range(3))


def _get_colors(n):
    return [_hexc(colorsys.hls_to_rgb(i / n, 0.4, 0.6)) for i in range(n)]


_tag_regex = re.compile(r"\s*\[[^\]]*\]")


def _stripped_map_name(map_name):
    return _tag_regex.sub("", map_name).strip()


def _get_global_faction_stats(db: LadderDatabase, mod: str):
    data = db.get_global_faction_stats(mod=mod)

    faction_colors = _get_colors(len(data))
    return dict(
        names=list(data.keys()),
        data=list(data.values()),
        total=sum(data.values()),
        colors=faction_colors,
    )


def _get_global_map_stats(db: LadderDatabase, season: Season):
    _data = db.get_map_stats(mod=season.mod, start_time=season.start.isoformat(), end_time=season.end.isoformat())
    hist = {}
    for map_title, count in _data.items():
        clean_map_title = _stripped_map_name(map_title)
        if clean_map_title in hist.keys():
            hist[clean_map_title] += count
        else:
            hist[clean_map_title] = count
    map_colors = _get_colors(len(hist))
    return dict(
        names=list(hist.keys()),
        data=list(hist.values()),
        total=sum(hist.values()),
        colors=map_colors,
    )


def _get_activity_stats(db: LadderDatabase, season: Season):
    start = season.start.isoformat()
    end = (season.end + timedelta(days=1)).isoformat()
    today = date.today()
    data = db.get_games_by_date_range(mod=season.mod, start=start, end=end)
    date_cursor = season.start
    records_base = {}
    while date_cursor <= season.end and date_cursor <= today:
        # Create a continous range of dates for the season duration
        records_base[date_cursor] = 0
        date_cursor += timedelta(days=1)
    # Merge actually played games into the continous date range
    records_base.update(data)
    # Transform dictionary keys to string format
    records = {key_date.isoformat(): value for key_date, value in records_base.items()}

    return dict(
        dates=list(records.keys()),
        data=list(records.values()),
        games_per_day=sum(records.values()) / len(records),
    )


def _get_player_ratings(db: LadderDatabase, mod: str, season_id: str, profile_id: str):
    condition = f"profile_id='{profile_id}' AND `mod`='{mod}' AND season_id='{season_id}'"
    res = db.fetch_table("rating", condition=condition)

    ratings = []
    for match in res:
        rating = match["value"]
        ratings.append(rating)

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


_cfg = dict(
    min_datapoints=10,
    datapoints=25,
)


def _scaled(a, m):
    n = len(a)
    nr = range(n)
    mr = [x * n / m for x in range(m)]
    return [round(x) for x in np.interp(mr, nr, a)]


def _get_player_faction_stats(db: LadderDatabase, mod: str, profile_id: str, season_id: Optional[str]):
    _data = db.get_player_faction_stats(mod=mod, profile_id=profile_id, season_id=season_id)
    faction_colors = _get_colors(len(_data))
    return dict(
        names=list(_data.keys()),
        data=list(_data.values()),
        total=sum(_data.values()),
        colors=faction_colors,
    )


def _get_player_map_stats(db: LadderDatabase, mod: str, profile_id: str, season_id: Optional[str] = None):
    _data = db.get_player_map_stats(mod=mod, profile_id=profile_id, season_id=season_id)
    hist = {}
    for map_title, stats in _data.items():
        clean_map_title = _stripped_map_name(map_title)
        if clean_map_title in hist.keys():
            hist[clean_map_title]["wins"] += stats["wins"]
            hist[clean_map_title]["losses"] += stats["losses"]
        else:
            hist[clean_map_title] = stats

    map_names = list(hist.keys())
    map_win_data = [m["wins"] for m in hist.values()]
    map_loss_data = [-int(m["losses"]) for m in hist.values()]
    return dict(
        names=map_names,
        win_data=map_win_data,
        loss_data=map_loss_data,
    )
