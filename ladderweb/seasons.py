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

import calendar
import datetime
from math import ceil

seasons_default = {
    "ra": {
        "all": "db-ra-all.sqlite3",
        "2m": "db-ra-2m.sqlite3"
    },
    "td": {
        "all": "db-td-all.sqlite3",
        "2m": "db-td-2m.sqlite3",
    }
}


def fill_yearly_seasons(seasons_dict=None,
                        start_year: int = datetime.date.today().year,
                        start_month: int = 1) -> dict:
    """Generate additional season entries based on 2-month periods

    Returns a populated dictionary with mod-ID keys (ra, td) at the top level and
    season identifiers as sub keys in descending order latest to earliest
    (e.g. 2022-6, 2022-5, ...); value of the season identifier key is always the
    expected SQLite database file name.

    Current period will always be identified as "2m".

    Database files have to be generated separately at the moment.

    Example:

    {
        "ra": {
            "all": "db-ra-all.sqlite3",
            "2m": "db-ra-2m.sqlite3",
            "2022-2": "db-ra-2022-2.sqlite3",
            "2022-1": "db-ra-2022-1.sqlite3",
            "2021-6": "db-ra-2021-6.sqlite3",
        },
        "td": {
            "all": "db-td-all.sqlite3",
            "2m": "db-td-2m.sqlite3",
            "2022-2": "db-td-2022-2.sqlite3",
            "2022-1": "db-td-2022-1.sqlite3",
            "2021-6": "db-td-2021-6.sqlite3",
        }
    }

    """
    if seasons_dict is None:
        seasons_dict = seasons_default

    # initialize variables
    today = datetime.date.today()
    current_month, current_year = today.month, today.year
    season_number = ceil(start_month / 2)
    season_year = start_year
    seasons = []

    while True:
        seasons.append((season_year, season_number))
        season_number += 1
        # omit the currently running season
        if season_year == current_year \
                and season_number * 2 >= current_month:
            break
        # increase year if we reach the 7th 2-month period
        if season_number == 7:
            season_year += 1
            season_number = 1

    # sort the seasons in descending chronological order, latest to earliest
    seasons.reverse()

    # put together the dictionary
    for year, season_number in seasons:
        for mod in ["ra", "td"]:
            season_name = f"{year}-{season_number}"
            db_file = f"db-{mod}-{year}-{season_number}.sqlite3"
            seasons_dict[mod][season_name] = db_file

    return seasons_dict


def get_season_info(season_string: str):
    """Returns display information based on a season-ID string

    Input may be '2m' for the current season or any valid combination
    of year/season-number e.g. '2022-1', '2021-5', ...

    Returns a dictionary containing start and end dates as datetime.date objects and
    a human-readable string explaining the duration
    """
    if season_string in ["all", "2m"]:
        today = datetime.date.today()
        year, season_number = today.year, ceil(today.month / 2)
        title = 'All time' if season_string == 'all' else 'Current season'
    else:
        year, season_number = season_string.split("-")
        title = season_string
    year = int(year)
    end_month = int(season_number) * 2
    start_month = end_month - 1
    _, end_day = calendar.monthrange(year, end_month)
    return dict(
        title=title,
        id=season_string,
        start=datetime.date(year, start_month, 1),
        end=datetime.date(year, end_month, end_day),
        duration='2 months',
    )
