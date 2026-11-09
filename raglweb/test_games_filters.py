import sqlite3
from pathlib import Path

from raglweb import app

SCHEMA_PATH = Path(__file__).parent.parent / "laddertools" / "ragl.sql"


def _make_client(tmp_path):
    db_path = tmp_path / "db.sqlite3"
    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA_PATH.read_text())
    db.executemany(
        "INSERT INTO players VALUES (?,?,?,?,?,?,?)",
        [
            (1, "Alpha", "", 1, 0, "Masters", None),
            (2, "Beta", "", 0, 1, "Masters", None),
            (3, "Gamma", "", 1, 0, "Minions", None),
            (4, "Delta", "", 0, 1, "Minions", None),
        ],
    )
    db.executemany(
        "INSERT INTO outcomes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "masters-game",
                "2026-11-01 20:00:00",
                "2026-11-01 20:30:00",
                "/tmp/masters.orarep",
                1,
                2,
                "gdi",
                "nod",
                "gdi",
                "nod",
                "map-uid",
                "Master Map",
            ),
            (
                "minions-game",
                "2026-11-02 20:00:00",
                "2026-11-02 20:30:00",
                "/tmp/minions.orarep",
                3,
                4,
                "gdi",
                "nod",
                "gdi",
                "nod",
                "map-uid",
                "Minion Map",
            ),
        ],
    )
    db.commit()
    db.close()

    app.config.update(TESTING=True, DATABASE=str(db_path))
    return app.test_client()


def test_games_page_shows_division_filter_and_player_search(tmp_path):
    body = _make_client(tmp_path).get("/games").get_data(as_text=True)

    assert 'name="division"' in body
    assert 'name="player"' in body
    assert '<option value="Masters">Masters</option>' in body
    assert '<option value="Minions">Minions</option>' in body


def test_games_can_be_filtered_by_division(tmp_path):
    body = _make_client(tmp_path).get("/games?division=Masters").get_data(as_text=True)

    assert "replay/masters-game" in body
    assert "replay/minions-game" not in body
    assert '<option value="Masters" selected>Masters</option>' in body


def test_games_can_be_searched_by_player_name_case_insensitively(tmp_path):
    body = _make_client(tmp_path).get("/games?player=GAMMA").get_data(as_text=True)

    assert "replay/minions-game" in body
    assert "replay/masters-game" not in body
    assert 'value="GAMMA"' in body


def test_games_with_no_filter_matches_show_empty_message(tmp_path):
    body = _make_client(tmp_path).get("/games?division=Minions&player=Alpha").get_data(as_text=True)

    assert "No games found." in body
    assert "replay/masters-game" not in body
    assert "replay/minions-game" not in body
