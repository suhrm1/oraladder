import datetime
from typing import Optional

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Date,
    Boolean,
    Engine,
    create_engine,
    PrimaryKeyConstraint,
    Integer,
    ForeignKey,
    text,
)

metadata_obj = MetaData()

config = Table(
    "config",
    metadata_obj,
    Column("key", String(256), primary_key=True),
    Column("value", String(2048), nullable=False),
)

algorithm = Table(
    "algorithm",
    metadata_obj,
    Column("id", String(40), primary_key=True),
    Column("title", String(80), nullable=False),
    Column("description", String(1024), nullable=True),
)

season = Table(
    "season",
    metadata_obj,
    Column("id", String(8), nullable=False),
    Column("mod", String(8), nullable=False),
    Column("title", String(64), nullable=False),
    Column("description", String(254), nullable=True),
    Column("start", String(10), nullable=True),
    Column("end", String(10), nullable=True),
    Column("duration", String(64), nullable=True),
    Column("active", Boolean, nullable=False, default=True),
    Column("algorithm", String(40), ForeignKey("algorithm.id"), nullable=False),
    Column("replay_path", String(256), nullable=False),
    Column("group", String(64), nullable=True),
    PrimaryKeyConstraint("id", "mod", name="season_pk"),
)

accounts = Table(
    "accounts",
    metadata_obj,
    Column("fingerprint", String(256), primary_key=True),
    Column("profile_id", Integer(), nullable=False),
    Column("profile_name", String(128), nullable=False),
    Column("banned", Boolean, nullable=False, default=False),
    Column("avatar_url", String(512), nullable=True),
)

broken_replays = Table(
    "broken_replays",
    metadata_obj,
    Column("filename", String(512), primary_key=True),
    Column("parse_date", Date(), nullable=False),
)

ranking = Table(
    "ranking",
    metadata_obj,
    Column("profile_id", Integer(), nullable=False),
    Column("season_id", String(8), nullable=False),
    Column("mod", String(8), nullable=False),
    Column("eligible", Boolean, nullable=False),
    Column("comment", String(512), nullable=True),
    Column("wins", Integer(), nullable=False),
    Column("losses", Integer(), nullable=False),
    Column("rating", Integer(), nullable=False),
    Column("difference", Integer(), nullable=False),
    Column("rank", Integer(), nullable=True),
)

game = Table(
    "game",
    metadata_obj,
    Column("hash", String(256), primary_key=True),
    Column("mod", String(8), nullable=False),
    Column("start_time", String(32), nullable=False),
    Column("end_time", String(32), nullable=False),
    Column("filename", String(512), nullable=False),
    Column("profile_id0", Integer(), nullable=False),
    Column("profile_id1", Integer(), nullable=False),
    Column("faction_0", String(32), nullable=False),
    Column("faction_1", String(32), nullable=False),
    Column("selected_faction_0", String(32), nullable=False),
    Column("selected_faction_1", String(32), nullable=False),
    Column("map_uid", String(64), nullable=False),
    Column("map_title", String(128), nullable=False),
)

rating = Table(
    "rating",
    metadata_obj,
    Column("replay_hash", String(256), nullable=False),
    Column("season_id", String(8), nullable=False),
    Column("mod", String(8), nullable=False),
    Column("profile_id", Integer(), nullable=False),
    Column("value", Integer(), nullable=False),
    Column("difference", Integer(), nullable=False, default=0),
)

highscore = Table(
    "highscore",
    metadata_obj,
    Column("mod_id", String(8), nullable=False),
    Column("season_group", String(64), nullable=False),
    Column("profile_id", Integer(), nullable=False),
    Column("profile_name", String(128), nullable=False),
    Column("avatar_url", String(512), nullable=True),
    Column("first_place", Integer(), nullable=False),
    Column("second_place", Integer(), nullable=False),
    Column("third_place", Integer(), nullable=False),
    Column("top_ten_percent", Integer(), nullable=False),
    Column("seasons", Integer(), nullable=False),
    Column("career_wins", Integer(), nullable=False),
    Column("career_games", Integer(), nullable=False),
)

history = Table(
    "history",
    metadata_obj,
    Column("mod_id", String(8), nullable=False),
    Column("season_id", String(8), nullable=False),
    Column("title", String(64), nullable=False),
    Column("season_group", String(64), nullable=False),
    Column("start", String(10), nullable=False),
    Column("end", String(10), nullable=True),
    Column("nb_games", Integer(), nullable=False),
    Column("avg_game_duration", String(8), nullable=True),
    Column("nb_players", Integer(), nullable=False),
    Column("first_place", Integer(), nullable=True),
    Column("second_place", Integer(), nullable=True),
    Column("third_place", Integer(), nullable=True),
    Column("algorithm", String(40), ForeignKey("algorithm.id"), nullable=False),
)

player_season_history = Table(
    "player_season_history",
    metadata_obj,
    Column("mod_id", String(8), nullable=False),
    Column("season_id", String(8), nullable=False),
    Column("profile_id", Integer(), nullable=False),
    Column("rank", Integer(), nullable=True),
    Column("rating", Integer(), nullable=False),
    Column("wins", Integer(), nullable=False),
    Column("losses", Integer(), nullable=False),
    Column("games", Integer(), nullable=False),
    Column("eligible", Boolean, nullable=False),
    Column("comment", String(512), nullable=True),
    Column("avg_game_duration", String(8), nullable=True),
    Column("players", Integer(), nullable=False),
    Column("ratio", String(8), nullable=True),
)

player_mod_stats = Table(
    "player_mod_stats",
    metadata_obj,
    Column("mod_id", String(8), nullable=False),
    Column("profile_id", Integer(), nullable=False),
    Column("wins", Integer(), nullable=False),
    Column("losses", Integer(), nullable=False),
    Column("nb_games", Integer(), nullable=False),
    Column("nb_seasons", Integer(), nullable=False),
    Column("avg_game_duration", String(8), nullable=True),
    Column("debut_date", Date(), nullable=False),
    Column("last_game_date", Date(), nullable=False),
    Column("ratio", String(8), nullable=True),
)

season_games = """CREATE OR REPLACE VIEW SeasonGames AS
(
    SELECT DISTINCT r0.`mod`,
        r0.season_id,
        g.hash,
        g.start_time,
        g.end_time,
        TIME_FORMAT(TIMEDIFF(TIMESTAMP(g.end_time), TIMESTAMP(g.start_time)), "%i:%S") AS duration,
        g.profile_id0,
        g.profile_id1,
        p0.profile_name AS p0_name,
        p1.profile_name AS p1_name,
        p0.banned as p0_banned,
        p1.banned as p1_banned,
        r0.value as rating0,
        r0.difference as diff0,
        r1.value as rating1,
        r1.difference as diff1,
        g.faction_0,
        g.faction_1,
        g.selected_faction_0, g.selected_faction_1, g.map_uid, g.map_title, g.filename
    FROM game g
        LEFT JOIN rating r0 ON g.profile_id0 = r0.profile_id AND r0.`mod`=g.`mod` AND r0.replay_hash=g.hash
        LEFT JOIN rating r1 ON g.profile_id1 = r1.profile_id AND r1.`mod`=g.`mod` AND r1.replay_hash=g.hash
            AND r1.season_id=r0.season_id
        LEFT JOIN accounts p0 ON p0.profile_id = g.profile_id0
        LEFT JOIN accounts p1 ON p1.profile_id = g.profile_id1
    ORDER BY g.end_time DESC
)"""
# for durations: use "%T" on TIME_FORMAT to get hh:mm:ss format


def init_mariadb(
    engine: Optional[Engine] = None,
    connection_str: str = "mariadb+mariadbconnector://ladder:ladderdbsecret@127.0.0.1:3306/ladder",
    replace: bool = False,
):
    if not Engine:
        engine: Engine = create_engine(connection_str)
    if replace:
        metadata_obj.drop_all(engine)
    metadata_obj.create_all(engine)

    with engine.begin() as txn:
        txn.execute(text(season_games))
