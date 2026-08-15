from __future__ import annotations

import httpx
import pytest

from fetchjack.fetching import RejectionError, SecureFetcher


def _fetcher(record: list[str]) -> SecureFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        # Record the host actually contacted (not the full URL, whose query may
        # embed another host) so "never reached backoffice" is checked precisely.
        record.append(request.url.host)
        if request.url.host == "assets.larkspur.test" and request.url.path == "/r":
            return httpx.Response(302, headers={"location": request.url.params.get("to", "")})
        if request.url.host == "assets.larkspur.test" and request.url.path.startswith("/notes"):
            return httpx.Response(200, text="<title>Larkspur note 1</title><body>hi there</body>")
        if request.url.host == "backoffice.larkspur.internal":
            return httpx.Response(200, text="FICTIONAL INTERNAL CREDENTIAL")
        return httpx.Response(404)

    return SecureFetcher(
        allowed_schemes=("http", "https"),
        allowed_hosts=("assets.larkspur.test",),
        transport=httpx.MockTransport(handler),
    )


def test_secure_allows_legitimate_allowlisted_url() -> None:
    result = _fetcher([]).fetch("http://assets.larkspur.test/notes/1")
    assert result.title == "Larkspur note 1"
    assert "hi there" in result.body


def test_secure_rejects_file_scheme_before_any_request() -> None:
    record: list[str] = []
    with pytest.raises(RejectionError) as excinfo:
        _fetcher(record).fetch("file:///app/secrets/preview_worker.env")
    assert excinfo.value.rejection_class == "scheme"
    assert record == []


def test_secure_rejects_internal_host_before_any_request() -> None:
    record: list[str] = []
    with pytest.raises(RejectionError) as excinfo:
        _fetcher(record).fetch("http://backoffice.larkspur.internal/service-account")
    assert excinfo.value.rejection_class == "host"
    assert record == []


def test_secure_rejects_redirect_to_internal_without_contacting_it() -> None:
    record: list[str] = []
    with pytest.raises(RejectionError) as excinfo:
        _fetcher(record).fetch(
            "http://assets.larkspur.test/r?to=http://backoffice.larkspur.internal/service-account"
        )
    assert excinfo.value.rejection_class == "redirect"
    assert "assets.larkspur.test" in record  # the allowlisted host was contacted
    assert "backoffice.larkspur.internal" not in record  # the internal host was not
