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
import logging
import os.path
from math import ceil
from typing import Optional

import yaml
from pydantic import BaseModel, ValidationError


class Season(BaseModel):
    id: str
    mod: str
    title: str
    database_file: str
    description: Optional[str]
    start: Optional[datetime.date]
    end: Optional[datetime.date]
    duration: Optional[str]

    def get_info(self) -> dict:
        if self.id == "2m" and self.start is None:
            # Calculate start and end dates of the current 2-month season
            today = datetime.date.today()
            start_date = datetime.date(year=today.year, month=today.month, day=1)
            if start_date.month % 2 == 0:
                start_date = start_date.replace(month=start_date.month - 1)
            _, end_day = calendar.monthrange(year=start_date.year, month=start_date.month + 1)
            end_date = datetime.date(year=today.year, month=start_date.month + 1, day=end_day)
            self.start = start_date
            self.end = end_date

        return dict(
            title=self.title,
            id=self.id,
            start=self.start,
            end=self.end,
            duration=self.duration,
        )


def load_yaml_season_config_from_directory(directory: str) -> {str: {str: Season}}:
    logging.debug(f"Loading season configuration from YAML files in {directory}")

    if not os.path.isdir(directory):
        logging.error(f"Not a directory")
        return None

    # initialize with default database keys and None values to impose static order
    seasons = {"ra": {"all": None, "2m": None}, "td": {"all": None, "2m": None}}

    for base_path, _, files in os.walk(directory):
        for filename in files:
            if os.path.splitext(filename)[1] in [".yml", ".yaml"]:
                logging.debug(f"Loading season configuration from {filename}")
                with open(os.path.join(base_path, filename), "r") as f:
                    yaml_content = yaml.safe_load(f.read())
                    # content should be a list of objects/dictionaries
                    if type(yaml_content) is list:
                        for item in yaml_content:
                            try:
                                season = Season(**item)
                                if season.mod in seasons.keys():
                                    seasons[season.mod][season.id] = season
                                else:
                                    seasons[season.mod] = {season.id: season}
                            except (ValidationError, TypeError) as e:
                                logging.warning(
                                    f'Could not parse "{item}" into Season object.',
                                    exc_info=False,
                                )

    logging.debug(f"Collected season configuration: {seasons}")
    return seasons
