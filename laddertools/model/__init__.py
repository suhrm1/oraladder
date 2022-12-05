import hashlib
from collections import UserDict

from laddertools.replay import GamePlayerInfo


class PlayerLookup(UserDict):
    """Connects a `GamePlayerInfo` (or its fingerprint) to a `_Player`.

    Several way to access a player:
        1) From a `GamePlayerInfo`: `lookup[result.player0]`
        2) From the unique id: `lookup[6003]`
        3) From the player name (since it's also unique): `lookup['morkel']`.
           Notice this only works for __getitem__ and not __setitem__. The name
           is also case-sensitive.
    """

    def __init__(self, accounts_db, ranking):
        super().__init__()
        self.accounts_db = accounts_db
        self.ranking = ranking
        self._names = {}

    def _insert_from_fingerprint(self, fingerprint):
        profile_id, name, avatar_url = self.accounts_db.get(fingerprint)
        self.data.setdefault(profile_id, Player(self.ranking, profile_id, name, avatar_url))
        self._names.setdefault(self.data[profile_id].name, self.data[profile_id])
        return self.data[profile_id]

    def __getitem__(self, obj):
        if isinstance(obj, GamePlayerInfo):
            return self._insert_from_fingerprint(obj.fingerprint)
        if isinstance(obj, str):  # we assume it's the name of the player, then.
            if obj not in self._names:
                raise KeyError(obj)
            return self._names[obj]
        return super().__getitem__(obj)

    def __setitem__(self, key, obj):
        assert isinstance(obj, Player)
        super().__setitem__(key, obj)
        self._names[obj.name] = obj

    def __repr__(self):
        return f"<PlayerLookup dictionary with {len(self.data)} items>"


class Player:
    def __init__(self, ranking, profile_id, name, avatar_url, banned=False):
        self.profile_id = profile_id
        self.name = name
        self.wins = 0
        self.losses = 0
        self.prv_rating = ranking.get_default_rating()
        self.rating = ranking.get_default_rating()
        self.avatar_url = avatar_url
        self.banned = banned

    def update_rating(self, new_rating):
        self.prv_rating = self.rating
        self.rating = new_rating

    def __repr__(self):
        return f"<Player {self.name}, id={self.profile_id}>"

    @property
    def sql_row(self):
        return (
            self.profile_id,
            self.name,
            self.avatar_url,
            self.banned,
            self.wins,
            self.losses,
            self.prv_rating.display_value,
            self.rating.display_value,
        )


class OutCome:
    def __init__(self, result, p0, p1):
        self._hash = hashlib.sha256(result.filename.encode()).hexdigest()
        self._filename = result.filename
        self._start_time = result.start_time
        self._end_time = result.end_time
        self._p0_profile_id = p0.profile_id
        self._p1_profile_id = p1.profile_id
        self._p0_rating0 = p0.prv_rating
        self._p1_rating0 = p1.prv_rating
        self._p0_rating1 = p0.rating
        self._p1_rating1 = p1.rating
        self._p0_faction = result.player0.faction
        self._p1_faction = result.player1.faction
        self._p0_selected_faction = result.player0.selected_faction
        self._p1_selected_faction = result.player1.selected_faction
        self._map_uid = result.map_uid
        self._map_title = result.map_title

    @staticmethod
    def _sql_date_fmt(dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def sql_row(self):
        return (
            self._hash,
            self._sql_date_fmt(self._start_time),
            self._sql_date_fmt(self._end_time),
            self._filename,
            self._p0_profile_id,
            self._p1_profile_id,
            self._p0_rating0.display_value,
            self._p1_rating0.display_value,
            self._p0_rating1.display_value,
            self._p1_rating1.display_value,
            self._p0_faction,
            self._p1_faction,
            self._p0_selected_faction,
            self._p1_selected_faction,
            self._map_uid,
            self._map_title,
        )
