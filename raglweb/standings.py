"""RAGL standings calculation.

The engine stores raw results in SQLite.  This module turns those results into
per-division standings, using the league's tie-breaking rules:

1. points (wins including forfeit wins)
2. direct head-to-head between tied players
3. fewer strikes
4. recursive head-to-head against higher-ranked players first, then lower-ranked
   players only after all higher-ranked comparisons failed
5. win rate, then name as a deterministic fallback

Players with status ``SF`` (manual season forfeit or automatic strike
disqualification) are removed from the ranking before any of this is applied.
"""

STRIKE_LIMIT_DEFAULT = 3


def _split_by_score(player_ids, scores):
    """Group players by score, highest score first."""
    groups = {}
    for profile_id in player_ids:
        groups.setdefault(scores[profile_id], []).append(profile_id)
    return [groups[score] for score in sorted(groups, reverse=True)]


def _rank_subgroups(subgroups, higher, lower_groups, head_to_head, strikes, winrate, names):
    """Rank subgroups in order, adding earlier subgroups to the higher set."""
    ordered = []
    for subgroup in subgroups:
        ordered.extend(
            _rank_group(
                subgroup,
                higher + ordered,
                lower_groups,
                head_to_head,
                strikes,
                winrate,
                names,
            )
        )
    return ordered


def _rank_group(group, higher, lower_groups, head_to_head, strikes, winrate, names):
    """Order a group of players tied on points."""
    if len(group) <= 1:
        return list(group)

    # 2. Direct head-to-head among the tied players.
    h2h_scores = {
        profile_id: sum(head_to_head.get((profile_id, opponent), 0) for opponent in group if opponent != profile_id)
        for profile_id in group
    }
    subgroups = _split_by_score(group, h2h_scores)
    if len(subgroups) > 1:
        return _rank_subgroups(subgroups, higher, lower_groups, head_to_head, strikes, winrate, names)

    # 3. Fewer strikes ranks higher.
    strike_scores = {profile_id: -strikes.get(profile_id, 0) for profile_id in group}
    subgroups = _split_by_score(group, strike_scores)
    if len(subgroups) > 1:
        return _rank_subgroups(subgroups, higher, lower_groups, head_to_head, strikes, winrate, names)

    # 4. Recursive head-to-head.  Walk the table from the top down: every
    # higher-ranked player is considered before any lower-ranked player.
    for opponent in higher:
        h2h_scores = {profile_id: head_to_head.get((profile_id, opponent), 0) for profile_id in group}
        subgroups = _split_by_score(group, h2h_scores)
        if len(subgroups) > 1:
            return _rank_subgroups(subgroups, higher, lower_groups, head_to_head, strikes, winrate, names)

    for lower_group in lower_groups:
        h2h_scores = {
            profile_id: sum(head_to_head.get((profile_id, opponent), 0) for opponent in lower_group)
            for profile_id in group
        }
        subgroups = _split_by_score(group, h2h_scores)
        if len(subgroups) > 1:
            return _rank_subgroups(subgroups, higher, lower_groups, head_to_head, strikes, winrate, names)

    # 5. Deterministic fallback.
    return sorted(group, key=lambda profile_id: (-winrate[profile_id], names[profile_id].casefold()))


def _rank_division(player_ids, points, head_to_head, strikes, winrate, names):
    """Rank all eligible players in a division."""
    point_groups = {}
    for profile_id in player_ids:
        point_groups.setdefault(points[profile_id], []).append(profile_id)

    groups = [point_groups[point] for point in sorted(point_groups, reverse=True)]
    ordered = []
    for index, group in enumerate(groups):
        ordered.extend(
            _rank_group(
                group,
                ordered,
                groups[index + 1 :],
                head_to_head,
                strikes,
                winrate,
                names,
            )
        )
    return ordered


def compute_standings(
    players,
    outcomes,
    forfeit_games,
    strike_counts,
    games_per_match,
    strike_limit=STRIKE_LIMIT_DEFAULT,
):
    """Build sorted standings per division.

    ``players`` must contain dicts with ``profile_id``, ``profile_name``,
    ``avatar_url``, ``wins``, ``losses``, ``division`` and ``status``.
    ``outcomes`` and ``forfeit_games`` must be iterables of ``(winner_id,
    loser_id)`` pairs.
    """
    rows = []
    rows_by_id = {}
    eligible_ids = set()

    for player in players:
        profile_id = int(player["profile_id"])
        strike_count = int(strike_counts.get(profile_id, 0))
        row = {
            "profile_id": profile_id,
            "name": player["profile_name"],
            "avatar_url": player["avatar_url"],
            "division": player["division"],
            "status": player["status"],
            "strikes": strike_count,
            "wins": int(player["wins"]),
            "losses": int(player["losses"]),
        }
        rows.append(row)
        rows_by_id[profile_id] = row
        if player["status"] != "SF" and strike_count < strike_limit:
            eligible_ids.add(profile_id)

    forfeit_wins = {}
    forfeit_losses = {}
    for winner, loser in forfeit_games:
        winner, loser = int(winner), int(loser)
        forfeit_wins[winner] = forfeit_wins.get(winner, 0) + 1
        forfeit_losses[loser] = forfeit_losses.get(loser, 0) + 1

    head_to_head = {}
    for winner, loser in outcomes:
        winner, loser = int(winner), int(loser)
        if winner in eligible_ids and loser in eligible_ids:
            head_to_head[(winner, loser)] = head_to_head.get((winner, loser), 0) + 1
    for winner, loser in forfeit_games:
        winner, loser = int(winner), int(loser)
        if winner in eligible_ids and loser in eligible_ids:
            head_to_head[(winner, loser)] = head_to_head.get((winner, loser), 0) + 1

    for row in rows:
        profile_id = row["profile_id"]
        row["wins"] += forfeit_wins.get(profile_id, 0)
        row["losses"] += forfeit_losses.get(profile_id, 0)
        row["played"] = row["wins"] + row["losses"]
        row["winrate"] = row["wins"] / row["played"] * 100 if row["played"] else 0
        row["eligible"] = profile_id in eligible_ids
        row["disqualified"] = row["strikes"] >= strike_limit

    standings = {}
    for division in sorted({player["division"] for player in players}):
        division_rows = [row for row in rows if row["division"] == division]
        eligible_rows = [row for row in division_rows if row["eligible"]]
        ineligible_rows = [row for row in division_rows if not row["eligible"]]

        max_matches = max(0, (len(eligible_rows) - 1) * games_per_match)
        for row in division_rows:
            row["max_matches"] = max_matches

        points = {row["profile_id"]: row["wins"] for row in eligible_rows}
        strikes = {row["profile_id"]: row["strikes"] for row in eligible_rows}
        winrate = {row["profile_id"]: row["winrate"] for row in eligible_rows}
        names = {row["profile_id"]: row["name"] for row in eligible_rows}

        ordered_ids = _rank_division(
            [row["profile_id"] for row in eligible_rows],
            points,
            head_to_head,
            strikes,
            winrate,
            names,
        )

        ordered_rows = []
        for rank, profile_id in enumerate(ordered_ids, 1):
            row = rows_by_id[profile_id]
            row["row_id"] = rank
            ordered_rows.append(row)

        ineligible_rows.sort(key=lambda row: (-row["wins"], -row["winrate"], row["name"].casefold()))
        for row in ineligible_rows:
            row["row_id"] = "SF"
        ordered_rows.extend(ineligible_rows)

        standings[division] = ordered_rows

    return standings
