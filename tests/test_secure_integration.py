"""Integration tests against the live secure service over real HTTP.

These run inside the containerized gate, where the ``secure`` service and the
fixtures are healthy before this container starts. They exercise the real
``httpx`` fetch, the real redirect from the fixture, and the real allowlist.
"""

from __future__ import annotations

import os

import httpx

_BASE = os.environ.get("SECURE_BASE_URL", "http://secure:8000")
_ADA = {"Authorization": "Bearer demo-token-ada"}
_GRACE = {"Authorization": "Bearer demo-token-grace"}

_ATTACKS = [
    "file:///app/secrets/preview_worker.env",
    "http://backoffice.larkspur.internal/service-account",
    "http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account",
]


def test_legitimate_preview_over_http_returns_deterministic_fields() -> None:
    response = httpx.post(
        f"{_BASE}/previews",
        headers=_ADA,
        json={"url": "http://assets.larkspur.test/notes/1"},
        timeout=10.0,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Larkspur note 1"
    assert "Fictional preview body for note 1" in body["body"]


def test_attacks_get_byte_identical_400_and_leave_history_unchanged() -> None:
    before = httpx.get(f"{_BASE}/previews", headers=_GRACE, timeout=10.0).json()
    responses = [
        httpx.post(f"{_BASE}/previews", headers=_GRACE, json={"url": url}, timeout=10.0)
        for url in _ATTACKS
    ]
    for response in responses:
        assert response.status_code == 400
    assert responses[0].content == responses[1].content == responses[2].content
    after = httpx.get(f"{_BASE}/previews", headers=_GRACE, timeout=10.0).json()
    assert after == before


def test_invalid_credentials_get_generic_401() -> None:
    for headers in ({}, {"Authorization": "Basic zzz"}, {"Authorization": "Bearer nope"}):
        response = httpx.get(f"{_BASE}/previews", headers=headers, timeout=10.0)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
