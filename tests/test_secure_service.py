from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fetchjack.fetching import FetchResult, RejectionError
from fetchjack.service import create_service_app

_USERS = {"demo-token-ada": "ada", "demo-token-grace": "grace"}

_LEGIT_URL = "http://assets.larkspur.test/notes/1"
_REJECT = {
    "file:///app/secrets/preview_worker.env": "scheme",
    "http://backoffice.larkspur.internal/service-account": "host",
    "http://assets.larkspur.test/r?to=x": "redirect",
}


class _FakeFetcher:
    def fetch(self, url: str) -> FetchResult:
        if url in _REJECT:
            raise RejectionError(_REJECT[url])
        if url == _LEGIT_URL:
            return FetchResult(_LEGIT_URL, "Larkspur note 1", "snippet", "Fictional body 1")
        return FetchResult(url, "", "", "")


def _auth(token: str = "demo-token-ada") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_service_app(
        fetcher=_FakeFetcher(),
        users=_USERS,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'svc.db'}",
    )
    with TestClient(app) as test_client:
        yield test_client


def test_missing_malformed_and_unknown_credentials_get_identical_401(client: TestClient) -> None:
    responses = [
        client.get("/previews"),
        client.get("/previews", headers={"Authorization": "Basic zzz"}),
        client.get("/previews", headers=_auth("demo-token-unknown")),
    ]
    for response in responses:
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    assert responses[0].content == responses[1].content == responses[2].content


def test_legitimate_preview_returns_201_and_appends_one_record(client: TestClient) -> None:
    response = client.post("/previews", headers=_auth(), json={"url": _LEGIT_URL})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Larkspur note 1"
    assert len(client.get("/previews", headers=_auth()).json()) == 1


def test_same_url_twice_appends_two_independent_records(client: TestClient) -> None:
    client.post("/previews", headers=_auth(), json={"url": _LEGIT_URL})
    client.post("/previews", headers=_auth(), json={"url": _LEGIT_URL})
    listed = client.get("/previews", headers=_auth()).json()
    assert len(listed) == 2
    assert listed[0]["id"] != listed[1]["id"]


def test_history_is_scoped_to_the_authenticated_user(client: TestClient) -> None:
    client.post("/previews", headers=_auth("demo-token-ada"), json={"url": _LEGIT_URL})
    assert len(client.get("/previews", headers=_auth("demo-token-ada")).json()) == 1
    assert len(client.get("/previews", headers=_auth("demo-token-grace")).json()) == 0


def test_rejections_are_byte_identical_400_with_no_record_and_safe_audit(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()  # drop startup output
    urls = list(_REJECT)
    responses = [client.post("/previews", headers=_auth(), json={"url": u}) for u in urls]
    for response in responses:
        assert response.status_code == 400
    assert responses[0].content == responses[1].content == responses[2].content
    assert client.get("/previews", headers=_auth()).json() == []

    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip().startswith("{")]
    events = [json.loads(ln) for ln in lines]
    assert [event["rejection_class"] for event in events] == ["scheme", "host", "redirect"]
    for event in events:
        assert event["user"] == "ada"
        assert event["outcome"] == "rejected"
        blob = json.dumps(event)
        assert "demo-token" not in blob
        assert "FICTIONAL" not in blob.upper()
