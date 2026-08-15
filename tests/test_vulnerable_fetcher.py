from __future__ import annotations

from pathlib import Path

import httpx

from fetchjack.fetching import VulnerableFetcher


def test_vulnerable_reads_local_file_via_file_scheme(tmp_path: Path) -> None:
    secret = tmp_path / "secret.env"
    secret.write_text("FICTIONAL TOKEN=abc123\n")
    result = VulnerableFetcher().fetch(f"file://{secret}")
    assert "FICTIONAL TOKEN=abc123" in result.body


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/r":
            return httpx.Response(302, headers={"location": request.url.params.get("to", "")})
        if request.url.host == "backoffice.larkspur.internal":
            return httpx.Response(200, text="internal service_account_token=zzz")
        return httpx.Response(200, text="benign")

    return httpx.MockTransport(handler)


def test_vulnerable_reaches_internal_host_directly() -> None:
    result = VulnerableFetcher(transport=_mock_transport()).fetch(
        "http://backoffice.larkspur.internal/service-account"
    )
    assert "service_account_token" in result.body


def test_vulnerable_follows_redirect_to_internal_host() -> None:
    result = VulnerableFetcher(transport=_mock_transport()).fetch(
        "http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account"
    )
    assert "service_account_token" in result.body
