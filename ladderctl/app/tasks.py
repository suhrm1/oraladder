import threading
import uuid
from datetime import datetime

from flask import current_app

from .activity import add_activity

_tasks = {}
_tasks_lock = threading.Lock()


def new_task(action, detail=""):
    """Create a task entry and return its id."""
    tid = uuid.uuid4().hex[:12]
    entry = {
        "id": tid,
        "action": action,
        "detail": detail,
        "status": "pending",
        "logs": [],
        "error": None,
        "created": datetime.now().strftime("%H:%M:%S"),
    }
    with _tasks_lock:
        _tasks[tid] = entry
    add_activity(action, detail, "pending")
    return tid


def update_task(tid, **kwargs):
    with _tasks_lock:
        if tid in _tasks:
            _tasks[tid].update(kwargs)


def append_log(tid, msg):
    with _tasks_lock:
        if tid in _tasks:
            _tasks[tid]["logs"].append(msg)


def get_task(tid):
    with _tasks_lock:
        return _tasks.get(tid)


def all_tasks():
    with _tasks_lock:
        return list(reversed(sorted(_tasks.values(), key=lambda t: t["created"])))[:30]


def run_background(tid, target, args=(), app=None):
    """Launch *target(*args)* in a daemon thread.

    If *app* is provided, push its application context before running
    so that ``current_app`` works inside the background thread.
    """
    update_task(tid, status="running")

    def wrapper():
        ctx = app.app_context() if app else None
        if ctx:
            ctx.push()
        try:
            target(tid, *args)
            update_task(tid, status="success")
        except Exception as exc:
            update_task(tid, status="error", error=str(exc))
            add_activity("Task failed", f"{exc.__class__.__name__}: {exc}", "error")
            if app:
                app.logger.exception("Background task %s failed", tid)
        finally:
            if ctx:
                ctx.pop()

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()
    return tid
