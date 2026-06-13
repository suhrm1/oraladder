from collections import deque
from datetime import datetime

_activity_log = deque(maxlen=50)


def add_activity(action, detail="", status="info"):
    """Append an entry to the in-memory activity log."""
    _activity_log.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "action": action,
            "detail": detail[:2000],
            "status": status,
        }
    )


def get_activity():
    """Return recent activity entries (newest first)."""
    return list(reversed(_activity_log))
