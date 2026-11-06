from datetime import date, datetime

from laddertools.replay import GamePlayerInfo, GameResult
from laddertools.utils import get_player_account, get_results


def _result(filename, p0, p1):
    return GameResult(
        datetime(2026, 11, 1, 20, 0),
        datetime(2026, 11, 1, 20, 30),
        filename,
        GamePlayerInfo(*p0),
        GamePlayerInfo(*p1),
        "map-uid",
        "Map Title",
    )


def test_get_results_keeps_legacy_call_signatures(monkeypatch):
    result = _result(
        "/replays/legacy.orarep",
        ("fingerprint-a", "Alpha", "gdi", "gdi"),
        ("fingerprint-b", "Beta", "nod", "nod"),
    )
    accounts_db = {
        result.player0.fingerprint: (1, "Alpha", ""),
        result.player1.fingerprint: (2, "Beta", ""),
    }
    period = {"start": date(2026, 11, 1), "end": date(2026, 11, 2)}
    outside_period = {"start": date(2026, 11, 3), "end": date(2026, 11, 4)}

    monkeypatch.setattr("laddertools.utils.replay.get_result", lambda filename: result)

    # These are the call styles used before the override parameter existed.
    assert get_results(accounts_db, ["legacy.orarep"]) == [result]
    assert get_results(accounts_db, ["legacy.orarep"], period) == [result]
    assert get_results(accounts_db, ["legacy.orarep"], period_dict=period) == [result]
    assert get_results(accounts_db, ["legacy.orarep"], outside_period) == []


def test_get_results_still_resolves_uncached_accounts(monkeypatch):
    result = _result(
        "/replays/legacy.orarep",
        ("fingerprint-a", "Alpha", "gdi", "gdi"),
        ("fingerprint-b", "Beta", "nod", "nod"),
    )
    profile_ids = {
        result.player0.fingerprint: 1,
        result.player1.fingerprint: 2,
    }

    def fake_update_account_cache(accounts_db, player):
        accounts_db[player.fingerprint] = (profile_ids[player.fingerprint], player.display_name, "")
        return True

    monkeypatch.setattr("laddertools.utils.replay.get_result", lambda filename: result)
    monkeypatch.setattr("laddertools.utils._update_account_cache", fake_update_account_cache)

    assert get_results({}, ["legacy.orarep"]) == [result]


def test_get_results_still_skips_unresolved_replays_without_overrides(monkeypatch):
    result = _result(
        "/replays/legacy.orarep",
        ("fingerprint-a", "Alpha", "gdi", "gdi"),
        ("fingerprint-b", "Beta", "nod", "nod"),
    )

    monkeypatch.setattr("laddertools.utils.replay.get_result", lambda filename: result)
    monkeypatch.setattr("laddertools.utils._update_account_cache", lambda accounts_db, player: False)

    assert get_results({}, ["legacy.orarep"]) == []


def test_get_results_supports_per_replay_overrides(monkeypatch):
    result = _result(
        "/replays/legacy.orarep",
        ("fingerprint-a", "Alpha", "gdi", "gdi"),
        ("fingerprint-b", "Beta", "nod", "nod"),
    )
    overrides = {"legacy.orarep": {"player0": 1, "player1": 2}}

    monkeypatch.setattr("laddertools.utils.replay.get_result", lambda filename: result)

    assert get_results({}, ["legacy.orarep"], overrides=overrides) == [result]


def test_get_player_account_without_overrides_matches_cache_lookup():
    player = GamePlayerInfo("fingerprint-a", "Alpha", "gdi", "gdi")
    account = (1, "Alpha", "")

    assert get_player_account({player.fingerprint: account}, player) == account
    assert get_player_account({player.fingerprint: None}, player) is None
    assert get_player_account({}, player) is None


def test_get_player_account_ignores_override_lookup_without_filename():
    player = GamePlayerInfo("fingerprint-a", "Alpha", "gdi", "gdi")
    account = (1, "Alpha", "")

    assert get_player_account({player.fingerprint: account}, player, overrides={"x.orarep": {"Alpha": 2}}) == account
