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
            (2, "Beta", "", 0, 1, "Minions", None),
        ],
    )
    db.commit()
    db.close()

    app.config.update(TESTING=True, DATABASE=str(db_path))
    return app.test_client()


def test_division_scoreboards_are_collapsed_by_default(tmp_path):
    response = _make_client(tmp_path).get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert body.count('<details class="scoreboard">') == 2
    assert '<details class="scoreboard" open' not in body
    assert "<summary>Masters</summary>" in body
    assert "<summary>Minions</summary>" in body


def test_footer_is_rendered_on_all_pages(tmp_path):
    client = _make_client(tmp_path)

    for path in ("/", "/games", "/playoffs", "/info"):
        response = client.get(path)
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "<footer>" in body
        assert "https://openra.net" in body
        assert "https://oraladder.net" in body
        assert "https://discord.gg/JyHZFbw" in body
