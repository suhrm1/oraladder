import datetime
from logging import Logger, getLogger
import os
from html import escape
from typing import Optional, List, Dict

import sqlalchemy.engine
import yaml
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.engine import CursorResult, Transaction
from sqlalchemy.future import create_engine

from ladderweb.model.seasons import Season
from ladderweb.model._sql import CREATE_STATEMENTS


class LadderDatabase:
    engine: sqlalchemy.engine.Engine

    def exec(self, sql: str, fetch: bool = False):
        sql = sql.replace("\n", "").replace("\t", "")
        with self.engine.connect() as conn:
            with conn.begin():
                cursor = conn.execute(text(sql))
                if fetch:
                    return cursor.fetchall()

    def __init__(
        self,
        connection_string: str,
        settings: Optional[dict],
        season_config_dir: Optional[str] = None,
        logger: Optional[Logger] = None,
    ):
        if not logger:
            self.logger = getLogger()
        else:
            self.logger = logger
        self.logger.debug(f"Loading main database with connection string {connection_string}")
        self.engine = create_engine(connection_string)
        self._initialize_database()
        if settings is not None:
            for key, value in settings.items():
                self.set_config_value(key, value)

        _seasons_initialized = False
        seasons = self.get_seasons()
        if "ra" in seasons and "td" in seasons:
            if "all" in seasons["ra"] and "all" in seasons["td"] and "2m" in seasons["ra"] and "2m" in seasons["td"]:
                _seasons_initialized = True
        if not _seasons_initialized and season_config_dir is not None:
            self.load_yaml_season_config_from_directory(directory=season_config_dir)

    def _initialize_database(self):
        # Create tables
        for table, create_statement in CREATE_STATEMENTS.items():
            self.exec(create_statement)

        # Seed algorithm descriptions
        algorithms = [
            {
                "id": "trueskill",
                "title": "TrueSkill",
                "description": "TrueSkill is a player ranking algorithm developed by Microsoft. OpenRA Ladder uses a "
                "mostly unmodified implementation of TrueSkill to calculate player skill ratings from "
                "their performances against other players.",
            },
            {
                "id": "openskill",
                "title": "OpenSkill",
                "description": "OpenSkill is an open source player ranking algorithm to predict player skill levels "
                "based on their performances agains other players. OpenRA Ladder uses a standard "
                "implementation with additional modifiers to prevent rating decrease on defeat as well "
                "as a minimum rating increase for every victory.",
            },
            {"id": "glicko", "title": "Glicko2", "description": "Glicko2 ranking algorithm."},
            {"id": "elo", "title": "Elo", "description": "Elo ranking algorithm."},
        ]
        self.batch_upsert(table="algorithm", batch=algorithms, primary_key="id")

    def insert_row(self, table: str, values: [], columns: Optional[List[str]], transaction: Transaction = None):
        if columns:
            cols = "(`" + "`, `".join(columns) + "`)"
        else:
            cols = ""
        row = "'" + "', '".join([escape(str(v)) if v is not None else "" for v in values]) + "'"
        sql = f"""INSERT INTO {table} {cols} VALUES ({row})"""
        if transaction is not None:
            transaction.connection.execute(sql)
        else:
            self.exec(sql)

    def batch_upsert(self, table: str, batch: List[dict], primary_key: str):
        existing = self.fetch_table(table)
        existing_ids = [row[primary_key] for row in existing]
        update_set = []
        insert_set = []
        for item in batch:
            if item[primary_key] in existing_ids:
                update_set.append(item)
            else:
                insert_set.append(item)
        for item in insert_set:
            self.insert_row(table, values=item.values(), columns=list(item.keys()))
        for item in update_set:
            self.update_row(table, values=item.values(), columns=list(item.keys()), primary_key=primary_key)

    @staticmethod
    def _result_to_list(result: CursorResult) -> List[dict]:
        result_list = []
        columns = [k for k in result.keys()]
        for row in result:
            result_list.append(dict(zip(columns, row)))
        return result_list

    def fetch_table(self, table: str, condition: Optional[str] = None, distinct: Optional[bool] = False) -> List[dict]:
        _dist = "DISTINCT" if distinct else ""
        sql = f"SELECT {_dist} * FROM {table}"
        if condition is not None:
            sql += f" WHERE {condition}"
        with self.engine.connect() as conn:
            with conn.begin():
                res = conn.execute(text(sql))
                return self._result_to_list(res)

    def update_row(self, table: str, values: [], columns: List[str], primary_key: str):
        row_dict = dict(zip(columns, values))
        pk_value = escape(str(row_dict[primary_key]))
        condition = f"{primary_key}='{pk_value}'"
        self.update_row_condition(table=table, values=values, columns=columns, condition=condition)

    def update_row_condition(self, table: str, values: [], columns: List[str], condition: str):
        row_dict = dict(zip(columns, values))
        payload = [f"`{col}`='{escape(str(val)) if val is not None else ''}'" for col, val in row_dict.items()]
        payload = ", ".join(payload)
        sql = f"""UPDATE {table} SET {payload} WHERE {condition}"""
        self.exec(sql)

    def batch_insert(self, table: str, batch: List[dict], transaction: Transaction = None):
        for item in batch:
            self.insert_row(table, values=item.values(), columns=list(item.keys()), transaction=transaction)

    def get_config_value(self, key: str) -> Optional[str]:
        with self.engine.connect() as conn:
            cursor = conn.execute(text(f"SELECT value FROM config WHERE key='{key}'"))
            return cursor.fetchone()[0]

    def set_config_value(self, key: str, value: str):
        self.batch_upsert("config", batch=[{"key": key, "value": value}], primary_key="key")

    def load_yaml_season_config_from_directory(self, directory: str):
        self.logger.debug(f"Loading season configuration from YAML files in {directory}")

        if not os.path.isdir(directory):
            self.logger.error(f"Not a directory")
            return None

        # initialize with default database keys and None values to impose static order
        seasons = {"ra": {"all": None, "2m": None}, "td": {"all": None, "2m": None}}
        existing_seasons = seasons.copy()

        for base_path, _, files in os.walk(directory):
            for filename in files:
                if os.path.splitext(filename)[1] in [".yml", ".yaml"]:
                    self.logger.debug(f"Loading season configuration from {filename}")
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
                                    self.logger.warning(
                                        f'Could not parse "{item}" into Season object.',
                                        exc_info=False,
                                    )
        self.logger.debug(f"Collected season configuration: {seasons}")

        # Collect existing seasons from database
        existing_season_list = [Season(**row) for row in self.fetch_table("season")]
        existing_mods = list(set([s.mod for s in existing_season_list]))
        for s in existing_season_list:
            existing_seasons[s.mod][s.id] = s
        self.logger.debug(f"Existing seasons: {existing_seasons}")

        # Update or insert seasons into database
        for mod, items in seasons.items():
            self.logger.debug(f"Existing seasons for {mod}: {list(existing_seasons[mod].keys())}")
            for season_id, season in items.items():
                if season is None:
                    continue
                if season_id in existing_seasons[mod].keys():
                    self.exec(f"DELETE FROM season WHERE mod='{mod}' AND id='{season_id}'")
                    self.logger.debug(f"Deleted {mod}.{season_id} from database")
                self.batch_insert("season", batch=[season.dict()])
                self.logger.debug(f"Inserted {season} into database")

    def get_seasons(self) -> Dict[str, Dict[str, Season]]:
        rows = self.fetch_table("season", condition="1=1 ORDER BY end DESC")
        seasons = {"ra": {}, "td": {}}
        for r in rows:
            s = Season(**r)
            seasons[s.mod][s.id] = s
        return seasons

    def get_banned_profile_ids(self) -> List[int]:
        ids = self.exec(f"SELECT DISTINCT profile_id FROM accounts WHERE banned='True';", fetch=True)
        ids = [item[0] for item in ids]
        return ids

    def get_leaderboard(self, mod: str, season_id: str):
        sql = f"""WITH players (profile_id, profile_name, avatar_url) AS
                    (SELECT DISTINCT profile_id, profile_name, avatar_url FROM accounts)
                SELECT r.*, a.profile_name, a.avatar_url FROM ranking r
                    LEFT JOIN players a
                    ON r.profile_id=a.profile_id
                    WHERE r.season_id='{season_id}' AND r.mod='{mod}'
                    ORDER BY r.rating DESC, (r.wins/r.losses)*100 DESC, (r.wins+r.losses) DESC"""
        with self.engine.connect() as conn:
            res = conn.execute(text(sql))
            return self._result_to_list(res)

    def get_highscore(self, mod_id: str = "ra", group_id: str = "seasons"):
        sql = f"""WITH players (profile_id, profile_name, avatar_url) AS
            (SELECT DISTINCT profile_id, profile_name, avatar_url FROM accounts WHERE banned!='True')
            SELECT p.*,
            (SELECT COUNT(r.rank) FROM ranking r
                LEFT JOIN season s ON r.season_id=s.id AND r.mod=s.mod
                WHERE profile_id=p.profile_id AND s.mod='{mod_id}' AND s.`group`='{group_id}'
                AND rank=1 AND s.active='False') as 'first_place',
            (SELECT COUNT(r.rank) FROM ranking r
                LEFT JOIN season s ON r.season_id=s.id AND r.mod=s.mod
                WHERE profile_id=p.profile_id  AND s.mod='{mod_id}' AND s.`group`='{group_id}'
                AND rank=2 AND s.active='False')  as 'second_place',
            (SELECT COUNT(r.rank) FROM ranking r
                LEFT JOIN season s ON r.season_id=s.id AND r.mod=s.mod
                WHERE profile_id=p.profile_id
                AND s.mod='{mod_id}' AND s.`group`='{group_id}' AND rank=3 AND s.active='False') as 'third_place',
            (SELECT COUNT(r1.rank) FROM ranking r1
                LEFT JOIN season s ON r1.season_id=s.id AND r1.mod=s.mod
                WHERE r1.profile_id=p.profile_id  AND s.mod='{mod_id}' AND s.`group`='{group_id}' AND s.active='False'
                AND r1.rank<=(10*(SELECT COUNT(r2.profile_id) FROM ranking r2
                WHERE r2.season_id=r1.season_id AND rank>0)/100)) as 'top_ten_percent',
            (SELECT COUNT(r.rank) FROM ranking r
                LEFT JOIN season s ON r.season_id=s.id AND r.mod=s.mod
                WHERE profile_id=p.profile_id AND s.mod='{mod_id}' AND s.`group`='{group_id}'
                AND rank>0 AND s.active='False') as seasons,
            (SELECT COUNT(DISTINCT g.hash) FROM SeasonGames g
                LEFT JOIN season s ON g.season_id=s.id AND g.mod=s.mod
                WHERE profile_id=g.profile_id0  AND s.`group`='{group_id}') as career_wins,
            (SELECT COUNT(DISTINCT g.hash) FROM SeasonGames g
                LEFT JOIN season s ON g.season_id=s.id AND g.mod=s.mod
                WHERE (profile_id=g.profile_id0 OR profile_id=g.profile_id1)
                    AND s.`group`='{group_id}') as career_games
            FROM players p WHERE (top_ten_percent > 0 OR first_place>0 OR second_place>0 OR third_place>0)
            ORDER BY 4 DESC, 5 DESC, 6 DESC, 7 DESC, 9 DESC, 8 DESC, 10 DESC;"""
        with self.engine.connect() as conn:
            res = conn.execute(text(sql))
            return self._result_to_list(res)

    def get_player_info(self, profile_id: str, mod_id: str = "ra", season_group: str = "seasons") -> dict:
        use_cache = False
        try:
            with self.engine.connect() as conn:
                query = (
                    f"SELECT MAX(end_time) FROM SeasonGames WHERE {profile_id} "
                    f"IN (profile_id0, profile_id1) AND mod='{mod_id}'"
                )
                last_game_date = datetime.datetime.fromisoformat(conn.execute(text(query)).fetchone()[0])
                query = f"SELECT * FROM player_mod_stats WHERE mod_id='{mod_id}' AND profile_id={profile_id}"
                cached_player_stats = dict(conn.execute(text(query)).fetchone())
                query = f"SELECT * FROM accounts WHERE profile_id={profile_id}"
                player_profile = dict(conn.execute(text(query)).fetchone())

            if cached_player_stats:
                # test if last game date matches
                if datetime.datetime.fromisoformat(cached_player_stats["last_game_date"]) == last_game_date:
                    stats = player_profile | cached_player_stats
                    # apply some key mappings for compatibility reasons
                    stats["seasons"] = stats["nb_seasons"]
                    stats["first_game"] = stats["debut_date"]
                    stats["last_game"] = stats["last_game_date"]
                    use_cache = True
        except TypeError as e:
            # This means, there was no entry in the database table, which is fine
            # We'll just produce the data instead of using cache
            pass

        if not use_cache:
            with self.engine.begin() as transaction:
                # We produce the player info and statistics from fact tables
                select = f"""SELECT
                *,
                (
                    SELECT COUNT(*) FROM game WHERE profile_id0={profile_id} AND mod='{mod_id}'
                ) as wins,
                (
                    SELECT COUNT(*) FROM game WHERE profile_id1={profile_id} AND mod='{mod_id}'
                ) as losses,
                (
                    SELECT strftime('%M:%S', AVG(julianday(end_time) - julianday(start_time)))
                    FROM game
                    WHERE {profile_id} IN (profile_id0, profile_id1) AND mod='{mod_id}'
                ) AS avg_game_duration,
                (
                    SELECT MIN(end_time) FROM game
                    WHERE {profile_id} IN (profile_id0, profile_id1) AND mod='{mod_id}'
                ) AS first_game,
                (
                    SELECT MAX(end_time) FROM game
                    WHERE {profile_id} IN (profile_id0, profile_id1) AND mod='{mod_id}'
                ) AS last_game,
                (
                    SELECT COUNT(DISTINCT s.id) FROM ranking r
                        LEFT JOIN season s ON r.season_id=s.id AND r.mod =s.mod
                    WHERE r.profile_id={profile_id} AND s.mod='{mod_id}' AND s.`group`='{season_group}'
                ) as seasons
                FROM accounts WHERE profile_id={profile_id} AND NOT banned
                LIMIT 1"""
                res: sqlalchemy.engine.row.Row = transaction.execute(text(select)).fetchone()
                stats = dict(res._mapping)

                # We create and insert an updated entry for the cache table
                mod_stats = {
                    "mod_id": mod_id,
                    "profile_id": profile_id,
                    "wins": stats["wins"],
                    "losses": stats["losses"],
                    "nb_games": stats["wins"] + stats["losses"],
                    "nb_seasons": stats["seasons"],
                    "avg_game_duration": stats["avg_game_duration"],
                    "debut_date": stats["first_game"],
                    "last_game_date": stats["last_game"],
                    "ratio": "{:.2f}%".format((stats["wins"] * 100) / (stats["wins"] + stats["losses"])),
                }
                transaction.execute(
                    text(f"DELETE FROM player_mod_stats " f"WHERE mod_id='{mod_id}' AND profile_id='{profile_id}';")
                )
                self.batch_insert(table="player_mod_stats", batch=[mod_stats], transaction=transaction)
                stats = stats | mod_stats

        return stats

    def check_player_active_season(self, mod: str, season_id: str, profile_id: int) -> bool:
        check = (
            f"SELECT COUNT(*) FROM SeasonGames sg "
            f"WHERE mod='{mod}' AND season_id='{season_id}' "
            f"AND (profile_id0='{profile_id}' OR profile_id1='{profile_id}');"
        )
        decision = bool(self.exec(check, fetch=True)[0][0])
        return decision

    def check_player_active_mod(self, mod: str, profile_id: str) -> bool:
        check = (
            f"SELECT COUNT(*) FROM SeasonGames sg "
            f"WHERE mod='{mod}' "
            f"AND (profile_id0='{profile_id}' OR profile_id1='{profile_id}');"
        )
        decision = bool(self.exec(check, fetch=True)[0][0])
        return decision

    def get_games(
        self, mod_id: str, start: datetime.date, end: datetime.date, order_by: str = "end_time ASC"
    ) -> List[dict]:
        query = f"SELECT * FROM game WHERE mod='{mod_id}' AND start_time>='{start}' AND end_time<='{end}'"
        if order_by:
            query += f" ORDER BY {order_by}"
        with self.engine.connect() as conn:
            res = conn.execute(text(query))
            return self._result_to_list(res)

    def get_global_faction_stats(self, mod: str) -> {}:
        stats = {}
        keys = ["wins", "losses"]
        for i in [0, 1]:
            res = self.exec(
                f"SELECT COUNT(*) as number, selected_faction_{i} as faction "
                f"FROM game WHERE mod='{mod}' GROUP BY selected_faction_{i};",
                fetch=True,
            )
            for count, faction in res:
                if faction in stats.keys():
                    stats[faction][keys[i]] = count
                else:
                    stats[faction] = {keys[i]: count}
        return {faction: win_loss.get("wins", 0) + win_loss.get("losses", 0) for faction, win_loss in stats.items()}

    def get_player_faction_stats(self, mod: str, profile_id: str, season_id: Optional[str] = None) -> {}:
        condition = f"p.profile_id='{profile_id}' AND g.mod='{mod}'"
        if season_id is not None:
            condition += f" AND g.season_id='{season_id}'"
        select = f"""SELECT DISTINCT (CASE
                WHEN g.profile_id0='{profile_id}' THEN selected_faction_0
                WHEN g.profile_id1='{profile_id}' THEN selected_faction_1
            END) AS faction, COUNT(DISTINCT hash) AS count
            FROM SeasonGames g LEFT JOIN accounts p ON p.profile_id IN (g.profile_id0, g.profile_id1)
            WHERE {condition}
            GROUP BY faction;"""
        res = self.exec(select, fetch=True)
        return {row[0]: row[1] for row in res}

    def get_player_map_stats(self, mod: str, profile_id: str, season_id: Optional[str] = None) -> {}:
        condition = f"(g.profile_id0='{profile_id}' OR g.profile_id1='{profile_id}') AND g.mod='{mod}'"
        if season_id is None:
            # In this case we need to join the season table to add the season group as a condition
            condition += f" AND s.`group`='seasons'"
            join = "LEFT JOIN season s ON (g.season_id=s.id AND s.mod=g.mod)"
        else:
            # For any specific season, no join is required
            condition += f" AND g.season_id='{season_id}'"
            join = ""
        select = f"""SELECT map_title,
                SUM((CASE WHEN g.profile_id0='{profile_id}' THEN 1 ELSE 0 END)) as wins,
                SUM((CASE WHEN g.profile_id1='{profile_id}' THEN 1 ELSE 0 END)) as losses
            FROM SeasonGames g
            {join}
            WHERE {condition}
            GROUP BY map_title;"""
        print(select)
        res = self.exec(select, fetch=True)
        return {row[0]: {"wins": row[1], "losses": row[2]} for row in res}

    def get_player_season_history(
        self,
        mod: str,
        profile_id: int,
        season_group: str = "seasons",
        season_id: Optional[str] = None,
        update_history: bool = False,
    ) -> {}:
        if season_id is not None:
            seasons = [self.get_seasons()[mod][season_id]]
        else:
            seasons = list(self.get_seasons()[mod].values())
        player_season_history = {}

        select_condition = f"mod_id='{mod}' AND profile_id='{profile_id}'"
        _history = {
            row["season_id"]: row for row in self.fetch_table("player_season_history", condition=select_condition)
        }

        for season in seasons:
            if season.group != season_group:
                continue
            if self.check_player_active_season(mod=mod, season_id=season.id, profile_id=profile_id):
                if season.id not in _history.keys() or update_history:
                    select = f"""SELECT rank, rating, wins, losses, (wins+losses) as games, eligible, comment,
                                    (
                                        SELECT strftime('%M:%S', AVG(julianday(g.end_time) - julianday(g.start_time)))
                                        FROM SeasonGames g
                                        WHERE r.profile_id IN (g.profile_id0, g.profile_id1)
                                        AND g.mod=r.mod AND g.season_id=r.season_id
                                    ) AS avg_game_duration,
                                    (
                                        SELECT COUNT(rank) FROM ranking r2
                                        WHERE r2.mod=r.mod AND r2.season_id=r.season_id
                                    ) AS players
                                    FROM ranking r
                                    WHERE r.profile_id='{profile_id}' AND r.mod='{mod}' AND r.season_id='{season.id}';"""
                    row: sqlalchemy.engine.row.Row = self.exec(select, fetch=True)[0]
                    stats = dict(row._mapping)
                    stats["ratio"] = "{:.2f}%".format(stats["wins"] / stats["games"] * 100)
                    stats["eligible"] = stats["eligible"] not in ["False", "0", 0]
                    stats["season_id"] = season.id
                    stats["mod_id"] = mod
                    stats["profile_id"] = profile_id
                    self.batch_insert("player_season_history", batch=[stats])
                else:
                    stats = _history[season.id]
                stats["season"] = season.get_info()
                stats["trophy"] = ""
                if stats["rank"] and stats["rank"] < 3:
                    stats["trophy"] = ["🥇", "🥈", "🥉"][stats["rank"] - 1]

                player_season_history[season.id] = stats
        return player_season_history

    def get_player_opponent_statistics(
        self,
        mod: str,
        player_id: int,
        season_id: Optional[str] = None,
    ):
        if season_id is None:
            # Condition to select statistics over all player games
            condition1 = f"""profile_id0={player_id} AND "mod"='{mod}'"""
            condition2 = f"""profile_id1={player_id} AND "mod"='{mod}'"""
            table = "game"
        else:
            # Condition to select statistics for a specific season
            condition1 = f"""profile_id0={player_id} AND "mod"='{mod}' AND season_id='{season_id}'"""
            condition2 = f"""profile_id1={player_id} AND "mod"='{mod}' AND season_id='{season_id}'"""
            table = "SeasonGames"

        query = f"""SELECT
            (SELECT DISTINCT profile_name FROM accounts WHERE profile_id=opponent_id) AS opponent_name,
            opponent_id,
            SUM(num_wins) + SUM(num_losses) AS played,
            SUM(num_wins) AS wins,
            SUM(num_losses) AS losses,
            ROUND(CAST(SUM(num_wins) AS FLOAT) / (CAST(SUM(num_wins) + SUM(num_losses) AS FLOAT)) * 100, 2) AS win_rate
            FROM
            (
                SELECT COUNT(`hash`) AS num_wins, 0 AS num_losses, profile_id1 AS opponent_id
                    FROM {table}
                    WHERE {condition1}
                    GROUP BY profile_id1
                UNION
                SELECT 0 AS num_wins, COUNT(`hash`) AS num_losses, profile_id0 AS opponent_id
                    FROM {table}
                    WHERE {condition2}
                    GROUP BY profile_id0
            )
            GROUP BY opponent_id
            ORDER BY played DESC, win_rate DESC, opponent_name ASC"""

        result: [sqlalchemy.engine.row.Row] = self.exec(query, fetch=True)
        return [dict(r._mapping) for r in result]

    def update_player_season_history(self, mod_id: str, season_id: Optional[str] = None, season_group: str = "seasons"):
        player_query = f"SELECT DISTINCT profile_id FROM rating WHERE mod='{mod_id}'"
        if season_id is not None:
            player_query += f" AND season_id='{season_id}'"
        profile_id_list = self.exec(sql=player_query, fetch=True)
        for tuple_item in profile_id_list:
            p_id = int(tuple_item[0])
            self.get_player_season_history(
                mod=mod_id, profile_id=p_id, season_id=season_id, season_group=season_group, update_history=True
            )

    def get_map_stats(self, mod: str, start_time: str, end_time: str) -> {}:
        select = (
            f"SELECT map_title, COUNT(*) AS count FROM game "
            f"WHERE mod='{mod}' AND start_time>='{start_time}' "
            f"AND end_time<='{end_time}'"
            f"GROUP BY map_title;"
        )
        res = self.exec(select, fetch=True)
        return {map_title: count for map_title, count in res}

    def get_season_stats(self, mod: str, season_id: str) -> {}:
        season_stats = self.get_season_history(mod_id=mod, season_id=season_id)[0]
        _players = self.exec(
            f"""SELECT DISTINCT r.profile_id, a.profile_name
            FROM ranking r LEFT JOIN accounts a ON r.profile_id=a.profile_id
            WHERE mod='{mod}';""",
            fetch=True,
        )
        _players = {p[0]: p[1] for p in _players}
        player_id_keys = ["first_place", "second_place", "third_place"]
        for key in player_id_keys:
            if season_stats[key]:
                _data = {key: {"profile_id": season_stats[key], "profile_name": _players[season_stats[key]]}}
            else:
                _data = {key: {"profile_id": None, "profile_name": None}}
            season_stats.update(_data)
        return season_stats

    def get_all_season_stats(self, mod: str, season_group: Optional[str] = None):
        season_stats = self.get_season_history(mod_id=mod, season_group=season_group)
        _players = self.exec(
            f"""SELECT DISTINCT r.profile_id, a.profile_name
            FROM ranking r LEFT JOIN accounts a ON r.profile_id=a.profile_id
            WHERE mod='{mod}';""",
            fetch=True,
        )
        _players = {p[0]: p[1] for p in _players}
        for season_row in season_stats:
            player_id_keys = ["first_place", "second_place", "third_place"]
            for key in player_id_keys:
                if season_row[key]:
                    _data = {key: {"profile_id": season_row[key], "profile_name": _players[season_row[key]]}}
                else:
                    _data = {key: None}
                season_row.update(_data)
        return season_stats

    def get_season_history(
        self, mod_id: Optional[str] = None, season_group: Optional[str] = None, season_id: Optional[str] = None
    ) -> List[Dict]:
        conditions = []
        if mod_id is not None:
            conditions.append(f"`mod_id`='{mod_id}'")
        if season_group is not None:
            conditions.append(f"`season_group`='{season_group}'")
        if season_id is not None:
            conditions.append(f"`season_id`='{season_id}'")
        if len(conditions):
            condition_str = "WHERE " + " AND ".join(conditions)
        else:
            condition_str = ""
        with self.engine.connect() as conn:
            query = f"SELECT * FROM history {condition_str} ORDER BY end DESC;"
            self.logger.debug(f"Querying season history: {query}")
            cursor = conn.execute(text(query))
            result = self._result_to_list(cursor)
            self.logger.debug(f"Number of historical seasons loaded: {len(result)}")

            if not result:
                # In case season history table has never been initialized, do that now and try again
                self.update_season_history(mod_id=mod_id, season_group=season_group, season_id=season_id)
                return self.get_season_history(mod_id=mod_id, season_group=season_group, season_id=season_id)
            else:
                return result

    def update_season_history(
        self, mod_id: Optional[str] = None, season_group: Optional[str] = None, season_id: Optional[str] = None
    ):
        conditions = []
        conditions_history_table = []
        if mod_id is not None:
            conditions.append(f"s.`mod`='{mod_id}'")
            conditions_history_table.append(f"`mod_id`='{mod_id}'")
        if season_group is not None:
            conditions.append(f"s.`group`='{season_group}'")
            conditions_history_table.append(f"`season_group`='{season_group}'")
        if season_id is not None:
            conditions.append(f"s.`id`='{season_id}'")
            conditions_history_table.append(f"`season_id`='{season_id}'")
        if len(conditions):
            condition_str = "WHERE " + " AND ".join(conditions)
            condition_history_table_str = "WHERE " + " AND ".join(conditions_history_table)
        else:
            condition_str, condition_history_table_str = "", ""

        query = f"""SELECT
            s.mod as mod_id,
            s.id as season_id,
            s.title as title,
            s.`group` as season_group,
            s.`start` as start,
            s.end as end,
            (
                SELECT COUNT(DISTINCT hash) FROM SeasonGames WHERE mod=s.mod AND season_id=s.id
            ) AS nb_games,
            (
                SELECT strftime('%M:%S', AVG(julianday(end_time) - julianday(start_time)))
                    FROM SeasonGames WHERE mod=s.mod AND season_id=s.id
            ) AS avg_game_duration,
            (
                SELECT COUNT(r.rank) FROM ranking r WHERE r.mod=s.mod AND r.season_id=s.id
            ) AS nb_players,
            (
                SELECT profile_id FROM ranking
                    WHERE mod=s.mod AND season_id=s.id AND rank=1
            ) as first_place,
            (
                SELECT profile_id FROM ranking
                    WHERE mod=s.mod AND season_id=s.id AND rank=2
            ) as second_place,
            (
                SELECT profile_id FROM ranking
                    WHERE mod=s.mod AND season_id=s.id AND rank=3
            ) as third_place,
            s.algorithm
        FROM season s
        LEFT JOIN algorithm a ON s.algorithm=a.id {condition_str}
        ORDER BY mod_id, season_group, end DESC;"""
        with self.engine.begin() as conn:
            cursor = conn.execute(text(query))
            data = self._result_to_list(cursor)
            conn.execute(text(f"DELETE FROM history {condition_history_table_str}"))
            self.batch_insert(table="history", batch=data, transaction=conn)

    def get_games_by_date_range(self, mod: str, start: str, end: str) -> {}:
        select = (
            f"SELECT date(end_time) as date, COUNT(*) as count FROM game "
            f"WHERE mod='{mod}' AND start_time>='{start}' AND end_time<='{end}' "
            f"GROUP BY date ORDER BY date ASC"
        )
        res = self.exec(select, fetch=True)
        return {date: count for date, count in res}

    def get_replay_filename(self, hash: str) -> str:
        select = f"SELECT filename FROM game WHERE hash='{hash}';"
        filename = self.exec(select, fetch=True)[0][0]
        return filename
