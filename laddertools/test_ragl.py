from datetime import date, datetime
from pathlib import Path

import yaml

from laddertools.ragl import (
    _get_players_outcomes,
    _parse_replay_overrides,
    _parse_strikes,
)
from laddertools.replay import GamePlayerInfo, GameResult


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


def test_parse_strikes_normalizes_date_and_reason():
    strikes = _parse_strikes(
        {
            "Strikes": [
                [1, date(2026, 11, 1), "First strike"],
                {"profile_id": 2, "date": "2026-11-02", "reason": "Second strike"},
            ]
        }
    )

    assert strikes == [
        (1, "2026-11-01", "First strike"),
        (2, "2026-11-02", "Second strike"),
    ]


def test_parse_replay_overrides_accepts_mapping_and_list():
    overrides = _parse_replay_overrides(
        {
            "Replay_Overrides": {
                "first.orarep": {"Alpha": 1, "player1": 2},
                "second.orarep": [["Beta", 3], [0, 4]],
            }
        }
    )

    assert overrides == {
        "first.orarep": {"Alpha": 1, "player1": 2},
        "second.orarep": {"Beta": 3, "0": 4},
    }


def test_replay_override_resolves_players_without_account_cache():
    players_info = {
        "Divisions": {"Masters": [[1, "Alpha"], [2, "Beta"]]},
        "Replay_Overrides": {
            "game.orarep": [
                ["player0", 1],
                ["beta", 2],
            ]
        },
    }
    overrides = _parse_replay_overrides(players_info)
    result = _result(
        "/replays/game.orarep",
        ("fingerprint-a", "Some smurf", "gdi", "gdi"),
        ("fingerprint-b", "Beta", "nod", "nod"),
    )

    players, outcomes, extra_outcomes = _get_players_outcomes({}, [result], players_info, overrides)
    players = list(players)

    assert len(outcomes) == 1
    assert not extra_outcomes
    assert outcomes[0].profile_pair == (1, 2)
    assert {player.profile_id: player.name for player in players} == {1: "Alpha", 2: "Beta"}


def test_three_strikes_disqualify_player_and_remove_results_from_points():
    players_info = {
        "Divisions": {"Masters": [[1, "Alpha"], [2, "Beta"]]},
        "Strikes": [
            [1, date(2026, 11, 1), "First strike"],
            [1, date(2026, 11, 2), "Second strike"],
            [1, date(2026, 11, 3), "Third strike"],
        ],
        "Replay_Overrides": {
            "game.orarep": [
                ["player0", 1],
                ["player1", 2],
            ]
        },
    }
    overrides = _parse_replay_overrides(players_info)
    result = _result(
        "/replays/game.orarep",
        ("fingerprint-a", "Alpha", "gdi", "gdi"),
        ("fingerprint-b", "Beta", "nod", "nod"),
    )

    players, outcomes, _ = _get_players_outcomes({}, [result], players_info, overrides)
    players = {player.profile_id: player for player in players}

    assert players[1].status == "SF"
    assert players[2].status is None
    assert players[1].wins == 0
    assert players[2].losses == 0
    assert len(outcomes) == 1


def test_all_existing_season_configs_remain_supported():
    config_paths = sorted(Path(__file__).parent.glob("ragl-s*.yml"))
    config_paths += sorted(Path(__file__).parent.glob("tdgl-s*.yml"))
    assert config_paths

    for config_path in config_paths:
        with config_path.open() as config_file:
            players_info = yaml.safe_load(config_file)

        # Older seasons predate the new optional sections.  Their absence must
        # not require changes to the season files.
        if "Strikes" not in players_info:
            assert _parse_strikes(players_info) == []
        if "Replay_Overrides" not in players_info:
            assert _parse_replay_overrides(players_info) == {}

        strike_limit = int(players_info.get("Strike_Limit", 3))
        strike_counts = {}
        for profile_id, _, _ in _parse_strikes(players_info):
            strike_counts[profile_id] = strike_counts.get(profile_id, 0) + 1
        forfeit = set(players_info.get("Forfeit", []))

        players, outcomes, extra_outcomes = _get_players_outcomes({}, [], players_info)
        players = list(players)

        assert players
        assert not outcomes
        assert not extra_outcomes
        for player in players:
            expected_status = (
                "SF"
                if player.profile_id in forfeit or strike_counts.get(player.profile_id, 0) >= strike_limit
                else None
            )
            assert player.status == expected_status
            assert player.strikes == strike_counts.get(player.profile_id, 0)
