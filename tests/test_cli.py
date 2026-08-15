from __future__ import annotations

import json

import httpx

from fetchjack.cli import CASES, AppReport, Observation, compute_verdict, render, run_matrix

_LEGIT = "http://assets.larkspur.test/notes/1"
_FILE = "file:///app/secrets/preview_worker.env"
_INTERNAL = "http://backoffice.larkspur.internal/service-account"
_REDIRECT = "http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account"

_SECURE = {_LEGIT: (201, "Fictional preview body for note 1")}
_VULNERABLE = {
    _FILE: (201, "PREVIEW_WORKER_TOKEN=x"),
    _INTERNAL: (201, "service_account_token=y"),
    _REDIRECT: (201, "service_account_token=y"),
    _LEGIT: (201, "Fictional preview body for note 1"),
}
_NAIVE = {
    _REDIRECT: (201, "service_account_token=y"),
    _LEGIT: (201, "Fictional preview body for note 1"),
}


def _client(outcomes: dict[str, tuple[int, str]]) -> httpx.Client:
    history: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if not request.headers.get("authorization", "").startswith("Bearer "):
            return httpx.Response(401, json={"detail": "unauthorized"})
        if request.method == "GET" and request.url.path == "/previews":
            return httpx.Response(200, json=list(history))
        if request.method == "POST" and request.url.path == "/previews":
            url = str(json.loads(request.content)["url"])
            status, body = outcomes.get(url, (400, "request rejected"))
            if status == 201:
                record = {"id": str(len(history) + 1), "submitted_url": url, "body": body}
                history.append(record)
                return httpx.Response(201, json=record)
            return httpx.Response(status, json={"error": "request rejected"})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _report(outcomes: dict[str, tuple[int, str]], role: str = "secure") -> AppReport:
    with _client(outcomes) as client:
        return run_matrix(client, {role: "http://app"}, "demo-token-ada")[0]


def test_matrix_scores_secure_app() -> None:
    report = _report(_SECURE)
    assert report.verdict.startswith("SECURE")
    assert (report.history_before, report.history_after) == (0, 1)


def test_matrix_scores_vulnerable_app() -> None:
    report = _report(_VULNERABLE, "vulnerable")
    assert report.verdict.startswith("VULNERABLE")
    assert report.history_after == 4


def test_matrix_scores_naive_app() -> None:
    report = _report(_NAIVE, "naive")
    assert report.verdict.startswith("NAIVE")
    assert report.history_after == 2


def _attacks(statuses: list[tuple[int, bool]]) -> list[Observation]:
    return [
        Observation(CASES[i], status, record_created=False, returned_marker=marker, body_excerpt="")
        for i, (status, marker) in enumerate(statuses)
    ]


def test_compute_verdict_pure() -> None:
    assert compute_verdict(_attacks([(400, False), (400, False), (400, False)])).startswith(
        "SECURE"
    )
    assert compute_verdict(_attacks([(201, True), (201, True), (201, True)])).startswith(
        "VULNERABLE"
    )
    assert compute_verdict(_attacks([(400, False), (400, False), (201, True)])).startswith("NAIVE")


def test_render_verbose_shows_hops_and_decisions() -> None:
    output = render([_report(_NAIVE, "naive")], verbose=True)
    assert "VERDICT:" in output
    assert "hop:" in output
    assert "decision:" in output
    assert "preview history:" in output
