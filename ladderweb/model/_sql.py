CREATE_STATEMENTS = {
    "season": """CREATE TABLE IF NOT EXISTS season (
        id              VARCHAR(63) NOT NULL,
        mod             VARCHAR(15) NOT NULL,
        title           VARCHAR(255) NOT NULL,
        description     TEXT NULL,
        start           DATE NOT NULL,
        end             DATE NULL,
        duration        VARCHAR(127) NULL,
        active          BOOLEAN NOT NULL DEFAULT 1,
        algorithm       VARCHAR(127) NOT NULL,
        replay_path     VARCHAR(255) NOT NULL,
        `group`           VARCHAR(63)
    );""",
    "accounts": """CREATE TABLE IF NOT EXISTS accounts (
        fingerprint  TEXT PRIMARY KEY,
        profile_id   INTEGER NOT NULL,
        profile_name TEXT NOT NULL,
        banned       BOOLEAN NOT NULL DEFAULT 0,
        avatar_url   TEXT
    );""",
    "ranking": """CREATE TABLE IF NOT EXISTS ranking (
        profile_id   INTEGER NOT NULL,
        season_id    VARCHAR(63) NOT NULL,
        mod          VARCHAR(15) NOT NULL,
        eligible     BOOLEAN NOT NULL,
        comment      TEXT,
        wins         INTEGER NOT NULL,
        losses       INTEGER NOT NULL,
        rating       INTEGER NOT NULL,
        difference   INTEGER NOT NULL,
        rank         INTEGER NOT NULL
    );""",
    "game": """CREATE TABLE IF NOT EXISTS game (
        hash                  TEXT NOT NULL PRIMARY KEY,
        mod                   VARCHAR(15) NOT NULL,
        start_time            TEXT NOT NULL,
        end_time              TEXT NOT NULL,
        filename              TEXT NOT NULL,
        profile_id0           INTEGER NOT NULL,
        profile_id1           INTEGER NOT NULL,
        faction_0             TEXT NOT NULL,
        faction_1             TEXT NOT NULL,
        selected_faction_0    TEXT NOT NULL,
        selected_faction_1    TEXT NOT NULL,
        map_uid               TEXT NOT NULL,
        map_title             TEXT NOT NULL
    );""",
    "rating": """CREATE TABLE IF NOT EXISTS rating (
        replay_hash TEXT NOT NULL,
        season_id   VARCHAR(63) NOT NULL,
        mod         VARCHAR(15) NOT NULL,
        profile_id  INTEGER NOT NULL,
        value       INTEGER NOT NULL,
        difference  INTEGER NOT NULL DEFAULT 0
    );""",
    "highscore": """CREATE TABLE IF NOT EXISTS highscore (
        mod_id              VARCHAR(15) NOT NULL,
        season_group        VARCHAR(63) NOT NULL,
        profile_id          INTEGER NOT NULL,
        profile_name        VARCHAR(255) NOT NULL,
        avatar_url          VARCHAR(511) NOT NULL,
        first_place         INTEGER NOT NULL,
        second_place        INTEGER NOT NULL,
        third_place         INTEGER NOT NULL,
        top_ten_percent     INTEGER NOT NULL,
        seasons             INTEGER NOT NULL,
        career_wins         INTEGER NOT NULL,
        career_games        INTEGER NOT NULL
    );""",
    "history": """CREATE TABLE IF NOT EXISTS history (
        mod_id              VARCHAR(15) NOT NULL,
        season_id           VARCHAR(63) NOT NULL,
        title               VARCHAR(255) NOT NULL,
        season_group        VARCHAR(63) NOT NULL,
        start               DATE NOT NULL,
        end                 DATE NULL,
        nb_games            INTEGER NOT NULL,
        avg_game_duration   VARCHAR(8),
        nb_players          INTEGER NOT NULL,
        first_place         INTEGER NOT NULL,
        second_place        INTEGER NOT NULL,
        third_place         INTEGER NOT NULL,
        algorithm           VARCHAR(127) NOT NULL
    );""",
    "player_season_history": """CREATE TABLE IF NOT EXISTS player_season_history (
        mod_id              VARCHAR(15) NOT NULL,
        season_id           VARCHAR(63) NOT NULL,
        profile_id          INTEGER NOT NULL,
        rank                INTEGER NOT NULL,
        rating              INTEGER NOT NULL,
        wins                INTEGER NOT NULL,
        losses              INTEGER NOT NULL,
        games               INTEGER NOT NULL,
        eligible            BOOLEAN NOT NULL,
        comment             TEXT,
        avg_game_duration   VARCHAR(8),
        players             INTEGER NOT NULL,
        ratio               VARCHAR(8)
    );""",
    "player_mod_stats": """CREATE TABLE IF NOT EXISTS player_mod_stats (
        mod_id              VARCHAR(15) NOT NULL,
        profile_id          INTEGER NOT NULL,
        wins                INTEGER NOT NULL,
        losses              INTEGER NOT NULL,
        nb_games            INTEGER NOT NULL,
        nb_seasons          INTEGER NOT NULL,
        avg_game_duration   VARCHAR(8),
        debut_date          DATE NOT NULL,
        last_game_date      DATE NOT NULL,
        ratio               VARCHAR(8)
    );""",
    "algorithm": """CREATE TABLE IF NOT EXISTS algorithm (
        id            VARCHAR(40) NOT NULL PRIMARY KEY,
        title         VARCHAR(80) NOT NULL,
        description   TEXT
    );""",
    "config": """CREATE TABLE IF NOT EXISTS config (
        key     VARCHAR(255) PRIMARY KEY,
        value   VARCHAR(2047)
    );""",
    "broken_replays": """CREATE TABLE IF NOT EXISTS broken_replays (
        filename     TEXT PRIMARY KEY,
        parse_date   DATE NOT NULL
    );""",
    "SeasonGames": """CREATE VIEW IF NOT EXISTS SeasonGames AS
        SELECT DISTINCT r0."mod", r0.season_id, g.hash, g.start_time, g.end_time,
            strftime('%M:%S', julianday(g.end_time) - julianday(g.start_time)) AS duration,
            g.profile_id0, g.profile_id1,
            p0.profile_name AS p0_name, p1.profile_name AS p1_name, p0.banned as p0_banned, p1.banned as p1_banned,
            r0.value as rating0, r0.difference as diff0, r1.value as rating1, r1.difference as diff1,
            g.faction_0 , g.faction_1, g.selected_faction_0, g.selected_faction_1, g.map_uid, g.map_title, g.filename
         FROM game g
            LEFT JOIN rating r0 ON g.profile_id0 = r0.profile_id AND r0."mod"=g."mod" AND r0.replay_hash=g.hash
            LEFT JOIN rating r1 ON g.profile_id1 = r1.profile_id AND r1."mod"=g."mod" AND r1.replay_hash=g.hash
                AND r1.season_id=r0.season_id
            LEFT JOIN accounts p0 ON p0.profile_id = g.profile_id0
            LEFT JOIN accounts p1 ON p1.profile_id = g.profile_id1
           ORDER BY g.end_time DESC;""",
}
