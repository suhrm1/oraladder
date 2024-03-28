from typing import Tuple

from ladderweb.model.seasons import Season

from ladderweb.model.database import LadderDatabase


def check_eligible(db: LadderDatabase, season: Season, profile_id: int) -> Tuple[bool, str]:
    judgement = True
    explanations: [str] = []

    # 1. Require at least 7 games against 3 unique opponents
    nr_games = 7
    nr_opponents = 3

    condition = (
        f"`mod`='{season.mod}' AND season_id='{season.id}' "
        f"AND (profile_id0='{profile_id}' OR profile_id1='{profile_id}')"
        f"AND p0_banned!=1 AND p1_banned!=1"
    )
    season_games = db.fetch_table(table="SeasonGames", condition=condition)

    opponents = set([row["profile_id0"] for row in season_games] + [row["profile_id1"] for row in season_games])
    opponents = opponents - {profile_id}

    if len(opponents) < nr_opponents:
        judgement = False
        explanations.append(
            f"Needs to play games against {nr_opponents} " f"unique opponents (only played {len(opponents)} yet)."
        )

    games_played = len(season_games)
    if games_played < nr_games:
        judgement = False
        explanations.append(f"Needs to play at least {nr_games} games.")

    explanation = " ".join(explanations) if len(explanations) else ""
    return judgement, explanation
