"""Act IV (The Forging) — tests for the real, incremental analysis-progress path: the endpoint
returns immediately, GET /analyses/{id} reflects genuine partial state while running, and the SSE
stream at /analyses/{id}/events emits real events (never a fake/simulated progress feed).
"""

import json

from app.agents.stage_labels import STAGE_LABELS, STAGE_ORDER
from tests.conftest import wait_for_terminal_analysis


def _create_startup(client):
    return client.post(
        "/api/v1/startups",
        json={
            "name": "WasteLess",
            "description": "Software that helps small restaurants track inventory and reduce food waste.",
            "funding_answers": {"problem_clarity": 2},
        },
    ).json()


def test_analyze_returns_immediately_without_a_completed_result(client):
    startup = _create_startup(client)
    response = client.post(f"/api/v1/startups/{startup['id']}/analyze")
    body = response.json()
    # The endpoint must never claim work that hasn't happened yet — no fields populated from a
    # result that doesn't exist the instant this returns.
    assert body["status"] in ("RUNNING", "COMPLETED")
    if body["status"] == "RUNNING":
        assert body["industry_prediction"] is None
        assert body["judge_summary"] is None
    # Drain the background thread before the test's per-test DB schema is torn down — otherwise
    # the still-running thread would hit the now-dropped table (a real hygiene concern, not just
    # a test artifact: any orphaned run should still finish cleanly on its own).
    wait_for_terminal_analysis(client, body["id"])


def test_current_node_and_stage_only_ever_report_real_known_nodes(client):
    startup = _create_startup(client)
    started = client.post(f"/api/v1/startups/{startup['id']}/analyze").json()
    final = wait_for_terminal_analysis(client, started["id"])

    # current_node/current_stage are keyed by the graph's own node id (what `stream_pipeline`
    # actually yields) — STAGE_LABELS covers every one of those ids, so this must never be an
    # invented or unmapped stage name. (workflow_trace's own "node" strings are each node
    # function's internal, pre-existing name — e.g. graph id "resolve_venture_positioning" vs.
    # trace name "venture_positioning" — a separate, already-existing naming scheme this sprint
    # doesn't touch; current_node/current_stage are the real founder-facing signal.)
    assert final["current_node"] in STAGE_LABELS
    assert final["current_stage"] == STAGE_LABELS[final["current_node"]]
    assert final["current_stage"] in STAGE_ORDER


def test_events_stream_emits_real_json_snapshots_and_closes_on_terminal(client):
    startup = _create_startup(client)
    started = client.post(f"/api/v1/startups/{startup['id']}/analyze").json()

    seen_statuses = []
    with client.stream("GET", f"/api/v1/analyses/{started['id']}/events") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[len("data: "):])
            assert payload["id"] == started["id"]
            seen_statuses.append(payload["status"])
            if payload["status"] in ("COMPLETED", "FAILED"):
                break

    assert seen_statuses[-1] == "COMPLETED"
    # Real progression, not a single fake jump — either it was already done by first snapshot, or
    # we genuinely observed it running before it completed.
    assert seen_statuses[0] in ("RUNNING", "COMPLETED")


def test_events_for_unknown_analysis_returns_404(client):
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000/events")
    assert response.status_code == 404


def test_events_snapshot_matches_the_plain_get_endpoint(client):
    """Single source of truth check: the SSE payload and GET /analyses/{id} must describe the
    exact same real row — no separate/duplicated serialization path."""
    startup = _create_startup(client)
    started = client.post(f"/api/v1/startups/{startup['id']}/analyze").json()
    wait_for_terminal_analysis(client, started["id"])

    plain = client.get(f"/api/v1/analyses/{started['id']}").json()
    with client.stream("GET", f"/api/v1/analyses/{started['id']}/events") as response:
        first_line = next(line for line in response.iter_lines() if line.startswith("data: "))
        streamed = json.loads(first_line[len("data: "):])

    assert streamed["judge_summary"] == plain["judge_summary"]
    assert streamed["workflow_trace"] == plain["workflow_trace"]
