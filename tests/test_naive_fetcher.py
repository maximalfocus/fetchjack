from __future__ import annotations

import httpx
import pytest

from fetchjack.fetching import NaiveFetcher, RejectionError

_ALLOWED = {"allowed_schemes": ("http", "https"), "allowed_hosts": ("assets.larkspur.test",)}


def _fetcher(record: list[str]) -> NaiveFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        record.append(request.url.host)
        if request.url.host == "assets.larkspur.test" and request.url.path == "/r":
            return httpx.Response(302, headers={"location": request.url.params.get("to", "")})
        if request.url.host == "backoffice.larkspur.internal":
            return httpx.Response(200, text="internal service_account_token=zzz")
        return httpx.Response(200, text="<title>benign</title>")

    return NaiveFetcher(
        allowed_schemes=("http", "https"),
        allowed_hosts=("assets.larkspur.test",),
        transport=httpx.MockTransport(handler),
    )


def test_naive_rejects_direct_file_scheme() -> None:
    with pytest.raises(RejectionError) as excinfo:
        _fetcher([]).fetch("file:///app/secrets/preview_worker.env")
    assert excinfo.value.rejection_class == "scheme"


def test_naive_rejects_direct_internal_host() -> None:
    with pytest.raises(RejectionError) as excinfo:
        _fetcher([]).fetch("http://backoffice.larkspur.internal/service-account")
    assert excinfo.value.rejection_class == "host"


def test_naive_follows_redirect_to_internal_without_revalidating() -> None:
    record: list[str] = []
    result = _fetcher(record).fetch(
        "http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account"
    )
    # It followed the redirect and reached the internal host — no hop re-validation.
    assert "service_account_token" in result.body
    assert "backoffice.larkspur.internal" in record
