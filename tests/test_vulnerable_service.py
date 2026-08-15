"""In-process vulnerable-service tests.

These build the vulnerable application in-process (the service layer with the
real ``VulnerableFetcher``) and exercise the section-4 outcomes. The file read is
the real baked fixture at ``/app/secrets/preview_worker.env`` and the internal
fetch is the real in-network ``backoffice`` fixture, both available inside the
verification gate. Building the fetcher here does not start the gated network
service (that opt-in is verified separately).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fetchjack.config import DEMO_USERS
from fetchjack.fetching import VulnerableFetcher
from fetchjack.service import create_service_app

_AUTH = {"Authorization": "Bearer demo-token-ada"}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_service_app(
        fetcher=VulnerableFetcher(),
        users=DEMO_USERS,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'vuln.db'}",
    )
    with TestClient(app) as test_client:
        yield test_client


def test_file_scheme_abuse_returns_secret_contents(client: TestClient) -> None:
    response = client.post(
        "/previews", headers=_AUTH, json={"url": "file:///app/secrets/preview_worker.env"}
    )
    assert response.status_code == 201
    assert "PREVIEW_WORKER_TOKEN" in response.json()["body"]


def test_internal_reach_returns_credential(client: TestClient) -> None:
    response = client.post(
        "/previews",
        headers=_AUTH,
        json={"url": "http://backoffice.larkspur.internal/service-account"},
    )
    assert response.status_code == 201
    assert "service_account_token" in response.json()["body"]
