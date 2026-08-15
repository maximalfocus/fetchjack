"""Consolidated FR-013 security regression matrix.

The per-application behaviours are proven in ``test_secure_*``, ``test_vulnerable_*``,
``test_naive_*``, and ``test_hermeticity``. This file adds the cross-application
and consolidated guarantees: the secure and vulnerable apps agree on a benign
input, the secure rejection reveals no target existence, and disposable state is
unchanged after the attack paths.

Apps are built in-process with their real fetchers; the legitimate fetch hits the
real in-network ``assets`` fixture available inside the gate.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fetchjack.config import DEMO_USERS
from fetchjack.fetching import SecureFetcher, VulnerableFetcher
from fetchjack.service import create_service_app

_AUTH = {"Authorization": "Bearer demo-token-ada"}
_SCHEMES = ("http", "https")
_HOSTS = ("assets.larkspur.test",)
_LEGIT = "http://assets.larkspur.test/notes/1"
_ATTACKS = [
    "file:///app/secrets/preview_worker.env",
    "http://backoffice.larkspur.internal/service-account",
    "http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account",
]


@pytest.fixture
def secure_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_service_app(
        fetcher=SecureFetcher(allowed_schemes=_SCHEMES, allowed_hosts=_HOSTS),
        users=DEMO_USERS,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'secure.db'}",
    )
    with TestClient(app) as client:
        yield client


@pytest.fixture
def vulnerable_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_service_app(
        fetcher=VulnerableFetcher(),
        users=DEMO_USERS,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'vuln.db'}",
    )
    with TestClient(app) as client:
        yield client


def test_secure_and_vulnerable_return_identical_body_for_benign_input(
    secure_client: TestClient, vulnerable_client: TestClient
) -> None:
    secure = secure_client.post("/previews", headers=_AUTH, json={"url": _LEGIT})
    vulnerable = vulnerable_client.post("/previews", headers=_AUTH, json={"url": _LEGIT})
    assert secure.status_code == 201
    assert vulnerable.status_code == 201
    for field in ("title", "snippet", "body"):
        assert secure.json()[field] == vulnerable.json()[field]


def test_legitimate_preview_appends_exactly_one_record(secure_client: TestClient) -> None:
    assert secure_client.get("/previews", headers=_AUTH).json() == []
    secure_client.post("/previews", headers=_AUTH, json={"url": _LEGIT})
    assert len(secure_client.get("/previews", headers=_AUTH).json()) == 1
    secure_client.post("/previews", headers=_AUTH, json={"url": _LEGIT})
    assert len(secure_client.get("/previews", headers=_AUTH).json()) == 2


def test_secure_rejection_discloses_no_target_existence(secure_client: TestClient) -> None:
    existing = secure_client.post(
        "/previews", headers=_AUTH, json={"url": "http://backoffice.larkspur.internal/x"}
    )
    missing = secure_client.post(
        "/previews", headers=_AUTH, json={"url": "http://nonexistent.larkspur.internal/x"}
    )
    assert existing.status_code == missing.status_code == 400
    # Identical response: the client cannot tell the internal host apart from a
    # host that does not exist (neither is contacted).
    assert existing.content == missing.content


def test_secure_history_byte_for_byte_unchanged_after_attacks(secure_client: TestClient) -> None:
    before = secure_client.get("/previews", headers=_AUTH).content
    responses = [secure_client.post("/previews", headers=_AUTH, json={"url": u}) for u in _ATTACKS]
    assert all(r.status_code == 400 for r in responses)
    assert responses[0].content == responses[1].content == responses[2].content
    after = secure_client.get("/previews", headers=_AUTH).content
    assert before == after
