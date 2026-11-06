from raglweb.standings import compute_standings


def _player(profile_id, name, wins=0, losses=0, status=None, division="Masters"):
    return dict(
        profile_id=profile_id,
        profile_name=name,
        avatar_url="",
        wins=wins,
        losses=losses,
        division=division,
        status=status,
    )


def _ranked_ids(standings, division="Masters"):
    return [row["profile_id"] for row in standings[division] if row["row_id"] != "SF"]


def test_sf_players_are_excluded_before_ranking():
    players = [
        _player(1, "Alpha", wins=1),
        _player(2, "Beta", wins=0),
        _player(3, "Gamma", wins=5, status="SF"),
    ]
    outcomes = [(1, 2), (3, 1)]
    standings = compute_standings(players, outcomes, [], {}, games_per_match=2)
    rows = standings["Masters"]

    assert _ranked_ids(standings) == [1, 2]
    assert rows[-1]["profile_id"] == 3
    assert rows[-1]["row_id"] == "SF"
    assert rows[-1]["max_matches"] == 2


def test_strike_limit_disqualifies_without_explicit_sf_status():
    players = [
        _player(1, "Alpha", wins=5),
        _player(2, "Beta", wins=0),
    ]
    standings = compute_standings(players, [], [], {1: 3}, games_per_match=2)
    rows = standings["Masters"]

    assert _ranked_ids(standings) == [2]
    assert rows[-1]["profile_id"] == 1
    assert rows[-1]["row_id"] == "SF"
    assert rows[-1]["disqualified"] is True


def test_direct_head_to_head_breaks_points_tie():
    players = [
        _player(1, "Alpha", wins=2),
        _player(2, "Beta", wins=2),
        _player(3, "Gamma", wins=0),
    ]
    outcomes = [(1, 2)]
    standings = compute_standings(players, outcomes, [], {}, games_per_match=2)

    assert _ranked_ids(standings) == [1, 2, 3]


def test_strikes_break_tie_after_head_to_head():
    players = [
        _player(1, "Alpha", wins=1),
        _player(2, "Beta", wins=1),
    ]
    standings = compute_standings(players, [], [], {1: 0, 2: 2}, games_per_match=2)

    assert _ranked_ids(standings) == [1, 2]


def test_higher_ranked_opponent_is_used_before_lower_ranked_opponent():
    players = [
        _player(1, "Alpha", wins=3),
        _player(2, "Beta", wins=1),
        _player(3, "Gamma", wins=1),
        _player(4, "Delta", wins=0),
    ]
    # Beta beat Alpha, while Gamma lost to Alpha.  Against the lower-ranked
    # Delta the result is the opposite, but Delta must not be considered first.
    outcomes = [(2, 1), (1, 3), (3, 4), (4, 2)]
    standings = compute_standings(players, outcomes, [], {}, games_per_match=2)

    assert _ranked_ids(standings) == [1, 2, 3, 4]


def test_lower_ranked_opponents_are_used_after_all_higher_ranked_opponents():
    players = [
        _player(1, "Alpha", wins=3),
        _player(2, "Beta", wins=1),
        _player(3, "Gamma", wins=1),
        _player(4, "Delta", wins=0),
    ]
    # Both lost to Alpha, so the tie remains after the higher-ranked player.
    # Gamma beat Delta, so Gamma wins the tiebreak against the lower-ranked
    # player.
    outcomes = [(1, 2), (1, 3), (3, 4), (4, 2)]
    standings = compute_standings(players, outcomes, [], {}, games_per_match=2)

    assert _ranked_ids(standings) == [1, 3, 2, 4]


def test_recursive_head_to_head_walks_down_the_table():
    players = [
        _player(1, "Alpha", wins=3),
        _player(2, "Beta", wins=2),
        _player(3, "Gamma", wins=1),
        _player(4, "Delta", wins=1),
        _player(5, "Epsilon", wins=0),
    ]
    # Gamma and Delta are equal against Alpha.  Against Beta, Delta has the
    # better result, so Beta is the second higher-ranked player that decides
    # the tie.
    outcomes = [(1, 3), (1, 4), (4, 2), (2, 3)]
    standings = compute_standings(players, outcomes, [], {}, games_per_match=2)

    assert _ranked_ids(standings) == [1, 2, 4, 3, 5]


def test_forfeit_games_are_included_in_points_and_head_to_head():
    players = [
        _player(1, "Alpha", wins=1),
        _player(2, "Beta", wins=2),
    ]
    # The forfeit gives Beta the second win and also the direct head-to-head
    # advantage, so Beta ranks above Alpha.
    forfeit_games = [(2, 1)]
    standings = compute_standings(players, [], forfeit_games, {}, games_per_match=2)

    assert _ranked_ids(standings) == [2, 1]
    rows = {row["profile_id"]: row for row in standings["Masters"]}
    assert rows[1]["wins"] == 1
    assert rows[1]["losses"] == 1
    assert rows[2]["wins"] == 3
