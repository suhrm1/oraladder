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
from typing import Optional
from pydantic import BaseModel


class Season(BaseModel):
    id: str
    mod: str
    title: str
    replay_path: str
    algorithm: str
    description: Optional[str] = None
    start: Optional[datetime.date] = None
    end: Optional[datetime.date] = None
    active: Optional[bool] = True
    duration: Optional[str] = None
    group: Optional[str] = "seasons"

    def __init__(self, *args, **kwargs):
        # Make sure data params get initialized correctly, e.g. not as empty strings
        for date_param in ["start", "end"]:
            if date_param in kwargs:
                if type(kwargs[date_param]) != datetime.date:
                    try:
                        kwargs[date_param] = datetime.date.fromisoformat(kwargs[date_param])
                    except:
                        kwargs[date_param] = None
        super().__init__(*args, **kwargs)

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

    def dict(self, *args, **kwargs):
        dictionary = super().dict()
        dictionary["active"] = 1 if self.active else 0
        return dictionary
