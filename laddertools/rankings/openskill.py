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
import copy

import openskill

from laddertools.rankings.abc import RankingBase
from laddertools.model import OutCome


class _RatingOpenskill:

    MINIMAL_INCREASE: int = 5
    internal: openskill.Rating

    def __init__(self, internal: openskill.Rating = None):
        self.internal = openskill.Rating() if internal is None else internal

    @property
    def value(self):
        val = openskill.ordinal(self.internal)
        if val < 0:
            val = 0
        return val

    @property
    def display_value(self):
        # XXX: needs more accuracy?
        return round(self.value * 100)

    def minimal_increase(self):
        min_increase = self.MINIMAL_INCREASE / 100
        self.internal.mu += min_increase


class RankingOpenskill(RankingBase):
    def record_result(self, winner_rating: _RatingOpenskill, loser_rating: _RatingOpenskill):
        [[r0], [r1]] = openskill.rate([[winner_rating.internal], [loser_rating.internal]])
        r0 = _RatingOpenskill(r0)
        r1 = _RatingOpenskill(r1)
        return r0, r1

    @classmethod
    def get_default_rating(cls):
        return _RatingOpenskill()

    def compute_ratings_from_series_of_games(self, games, player_lookup):
        player_ratings = {}
        game_ratings = []
        for g in games:
            p0 = player_lookup[g.player0]
            p1 = player_lookup[g.player1]
            r0 = player_ratings.get(p0, self.get_default_rating())
            r1 = player_ratings.get(p1, self.get_default_rating())

            r0_new, r1_new = self.record_result(r0, r1)
            player_ratings[p0] = r0_new
            player_ratings[p1] = r1_new

            item = (r0_new, r1_new)
            game_ratings.append(item)

        outcomes = []
        for result, (r0, r1) in zip(games, game_ratings):
            p0 = player_lookup[result.player0]
            p1 = player_lookup[result.player1]
            if r0.display_value > p0.rating.display_value + p0.rating.MINIMAL_INCREASE:
                p0.update_rating(r0)
            else:
                # We update the rating with a minimally increased version
                rating_clone = copy.deepcopy(p0.rating)
                rating_clone.minimal_increase()
                p0.update_rating(rating_clone)
            if r1.display_value > p1.rating.display_value:
                p1.update_rating(r1)
            else:
                p1.update_rating(p1.rating)
            p0.wins += 1
            p1.losses += 1
            outcomes.append(OutCome(result, p0, p1))
        players = player_lookup.values()
        return players, outcomes
