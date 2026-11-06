import sqlite3
from pathlib import Path

from raglweb import app

SCHEMA_PATH = Path(__file__).parent.parent / "laddertools" / "ragl.sql"


def _make_database(tmp_path):
    db_path = tmp_path / "db.sqlite3"
    replay_path = tmp_path / "replays" / "game.orarep"
    replay_path.parent.mkdir()
    replay_path.write_text("replay-content")

    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA_PATH.read_text())
    db.executemany(
        "INSERT INTO players VALUES (?,?,?,?,?,?,?)",
        [
            (1, "Alpha", "", 1, 0, "Masters", None),
            (2, "Beta", "", 0, 1, "Masters", None),
        ],
    )
    db.executemany(
        "INSERT INTO outcomes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "regular-hash",
                "2026-11-01 20:00:00",
                "2026-11-01 20:30:00",
                str(replay_path),
                1,
                2,
                "gdi",
                "nod",
                "gdi",
                "nod",
                "map-uid",
                "Map Title",
            ),
            (
                "missing-file-hash",
                "2026-11-01 20:00:00",
                "2026-11-01 20:30:00",
                str(tmp_path / "missing.orarep"),
                1,
                2,
                "gdi",
                "nod",
                "gdi",
                "nod",
                "map-uid",
                "Map Title",
            ),
            (
                "unregistered-player-hash",
                "2026-11-01 20:00:00",
                "2026-11-01 20:30:00",
                str(replay_path),
                999,
                2,
                "gdi",
                "nod",
                "gdi",
                "nod",
                "map-uid",
                "Map Title",
            ),
        ],
    )
    db.execute(
        "INSERT INTO playoff_outcomes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "playoff-hash",
            "2026-11-01 20:00:00",
            "2026-11-01 20:30:00",
            str(replay_path),
            1,
            2,
            "gdi",
            "nod",
            "gdi",
            "nod",
            "map-uid",
            "Map Title",
        ),
    )
    db.commit()
    db.close()
    return db_path


def _client(tmp_path):
    app.config.update(TESTING=True, DATABASE=str(_make_database(tmp_path)))
    return app.test_client()


def test_replay_route_serves_regular_outcome(tmp_path):
    client = _client(tmp_path)

    response = client.get("/replay/regular-hash")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "replay-content"


def test_replay_route_returns_404_for_unknown_hash(tmp_path):
    client = _client(tmp_path)

    assert client.get("/replay/unknown-hash").status_code == 404


def test_replay_route_can_serve_playoff_outcome(tmp_path):
    client = _client(tmp_path)

    assert client.get("/replay/playoff-hash").status_code == 200


def test_replay_route_returns_404_when_file_is_missing(tmp_path):
    client = _client(tmp_path)

    assert client.get("/replay/missing-file-hash").status_code == 404


def test_replay_route_returns_404_when_player_is_unregistered(tmp_path):
    client = _client(tmp_path)

    assert client.get("/replay/unregistered-player-hash").status_code == 404


def test_replay_playoff_route_serves_playoff_outcome(tmp_path):
    client = _client(tmp_path)

    assert client.get("/replay_playoff/playoff-hash").status_code == 200


def test_replay_playoff_route_returns_404_for_unknown_hash(tmp_path):
    client = _client(tmp_path)

    assert client.get("/replay_playoff/unknown-hash").status_code == 404
