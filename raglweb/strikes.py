import sqlite3
from datetime import datetime


def _has_strikes_table(db):
    try:
        db.execute("SELECT 1 FROM strikes LIMIT 1")
    except sqlite3.OperationalError:
        return False
    return True


def get_strike_stats(db):
    """Return a mapping of profile ID to strike count."""
    if not _has_strikes_table(db):
        return {}
    cur = db.execute("SELECT profile_id, COUNT(*) FROM strikes GROUP BY profile_id")
    return {int(profile_id): int(count) for profile_id, count in cur}


def get_player_strikes(db, profile_id):
    """Return a player's strike history, oldest first."""
    if not _has_strikes_table(db):
        return []
    cur = db.execute(
        """
        SELECT decision_timestamp, reason
        FROM strikes
        WHERE profile_id = :profile_id
        ORDER BY decision_timestamp ASC
        """,
        dict(profile_id=profile_id),
    )
    strikes = []
    for timestamp, reason in cur:
        try:
            formatted_date = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            formatted_date = timestamp
        strikes.append(dict(date=formatted_date, reason=reason))
    return strikes
