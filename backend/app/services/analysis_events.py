"""In-memory pub/sub so the SSE endpoint (app/api/v1/analyses.py's `stream_analysis_events`) can
be woken up immediately when the background analysis thread (see
`analysis_service._execute_analysis_stream`) persists a new node's real result, instead of
polling the database on a timer.

Deliberately not a message queue or a new "AI capability" — it carries no analysis data itself,
only a wake-up signal; the SSE handler always re-reads the real Analysis row from the database as
the single source of truth after being woken. Process-local (an in-memory dict), which is
sufficient for this single-instance FastAPI deployment; a multi-process deployment would need a
real broker instead, but that's an infrastructure concern orthogonal to this sprint's scope.
"""

from __future__ import annotations

import queue
import threading

_lock = threading.Lock()
_subscribers: dict[str, list[queue.Queue]] = {}


def subscribe(analysis_id: str) -> queue.Queue:
    q: queue.Queue = queue.Queue()
    with _lock:
        _subscribers.setdefault(analysis_id, []).append(q)
    return q


def unsubscribe(analysis_id: str, q: queue.Queue) -> None:
    with _lock:
        subscribers = _subscribers.get(analysis_id)
        if not subscribers:
            return
        if q in subscribers:
            subscribers.remove(q)
        if not subscribers:
            _subscribers.pop(analysis_id, None)


def publish(analysis_id: str, event: dict) -> None:
    with _lock:
        subscribers = list(_subscribers.get(analysis_id, []))
    for q in subscribers:
        q.put(event)
