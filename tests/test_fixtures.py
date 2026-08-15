"""Fixture-target tests.

These exercise the in-network fixtures over HTTP and therefore run inside the
containerized verification gate, where the ``assets`` and ``backoffice``
services are healthy before this container starts. Running them requires the
fixture network, matching the project's Docker-only verification boundary.
"""

from __future__ import annotations

import os

import httpx

ASSETS = os.environ.get("ASSETS_BASE_URL", "http://assets.larkspur.test")
INTERNAL = os.environ.get("INTERNAL_BASE_URL", "http://backoffice.larkspur.internal")


def test_note_content_is_byte_identical_across_requests() -> None:
    first = httpx.get(f"{ASSETS}/notes/1", timeout=5.0)
    second = httpx.get(f"{ASSETS}/notes/1", timeout=5.0)
    assert first.status_code == 200
    assert first.content == second.content
    assert b"Larkspur note 1" in first.content
    assert b"Fictional" in first.content


def test_distinct_notes_differ() -> None:
    one = httpx.get(f"{ASSETS}/notes/1", timeout=5.0).content
    two = httpx.get(f"{ASSETS}/notes/2", timeout=5.0).content
    assert one != two


def test_redirect_endpoint_issues_302_without_following() -> None:
    target = "http://backoffice.larkspur.internal/service-account"
    resp = httpx.get(f"{ASSETS}/r", params={"to": target}, follow_redirects=False, timeout=5.0)
    assert resp.status_code == 302
    assert resp.headers["location"] == target


def test_internal_credential_is_fictional_and_deterministic() -> None:
    first = httpx.get(f"{INTERNAL}/service-account", timeout=5.0)
    second = httpx.get(f"{INTERNAL}/service-account", timeout=5.0)
    assert first.status_code == 200
    assert first.content == second.content
    assert b"FICTIONAL DEMO FIXTURE" in first.content


def test_allowlisted_and_internal_hosts_are_distinct() -> None:
    assert ASSETS != INTERNAL
    assert "assets.larkspur.test" in ASSETS
    assert "backoffice.larkspur.internal" in INTERNAL


def test_local_fixture_secret_file_declares_itself_fictional() -> None:
    with open("/app/secrets/preview_worker.env", encoding="utf-8") as handle:
        contents = handle.read()
    assert "FICTIONAL" in contents.upper()
    assert "PREVIEW_WORKER" in contents.upper()
