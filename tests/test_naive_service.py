"""In-process naive-service tests.

The direct-rejection tests need no network (both apps reject the submitted URL
before fetching). The redirect-bypass test performs the real allowlisted-host
redirect to the real in-network internal fixture, available inside the gate.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fetchjack.config import DEMO_USERS
from fetchjack.fetching import NaiveFetcher, SecureFetcher
from fetchjack.service import create_service_app

_AUTH = {"Authorization": "Bearer demo-token-ada"}
_SCHEMES = ("http", "https")
_HOSTS = ("assets.larkspur.test",)
_DIRECT_ATTACKS = [
    "file:///app/secrets/preview_worker.env",
    "http://backoffice.larkspur.internal/service-account",
]


@pytest.fixture
def naive_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_service_app(
        fetcher=NaiveFetcher(allowed_schemes=_SCHEMES, allowed_hosts=_HOSTS),
        users=DEMO_USERS,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'naive.db'}",
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def secure_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_service_app(
        fetcher=SecureFetcher(allowed_schemes=_SCHEMES, allowed_hosts=_HOSTS),
        users=DEMO_USERS,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'secure.db'}",
    )
    with TestClient(app) as test_client:
        yield test_client


def test_naive_rejects_direct_attacks_identically_to_secure(
    naive_client: TestClient, secure_client: TestClient
) -> None:
    for url in _DIRECT_ATTACKS:
        naive = naive_client.post("/previews", headers=_AUTH, json={"url": url})
        secure = secure_client.post("/previews", headers=_AUTH, json={"url": url})
        assert naive.status_code == 400
        assert secure.status_code == 400
        assert naive.content == secure.content
    assert naive_client.get("/previews", headers=_AUTH).json() == []


def test_naive_redirect_bypass_returns_internal_credential(naive_client: TestClient) -> None:
    response = naive_client.post(
        "/previews",
        headers=_AUTH,
        json={
            "url": "http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account"
        },
    )
    assert response.status_code == 201
    assert "service_account_token" in response.json()["body"]
