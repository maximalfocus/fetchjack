"""Server-side fetch policies.

The shared service layer is parameterised by a ``Fetcher``. This module defines
the fetch contract, the shared preview-field extraction, and the **secure**
fetcher, which enforces a scheme and host allowlist on every request it makes,
including each redirect hop, validating a redirect target *before* contacting it.

The vulnerable and naive fetchers are added in later slices.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlsplit

import httpx

_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_SNIPPET_LEN = 120


@dataclass(frozen=True)
class FetchResult:
    final_url: str
    title: str
    snippet: str
    body: str


class RejectionError(Exception):
    """A target was rejected by the secure allowlist.

    ``rejection_class`` is one of ``"scheme"``, ``"host"``, or ``"redirect"``.
    It is used only for the server-side audit event and is never disclosed to
    the client.
    """

    def __init__(self, rejection_class: str) -> None:
        super().__init__(rejection_class)
        self.rejection_class = rejection_class


class Fetcher(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


def parse_preview(final_url: str, text: str) -> FetchResult:
    """Extract deterministic preview fields from fetched content.

    Shared by every application so that identical fetched bytes yield an
    identical preview record regardless of which application fetched them.
    """
    match = _TITLE_RE.search(text)
    title = match.group(1).strip() if match else ""
    snippet = " ".join(text.split())[:_SNIPPET_LEN]
    return FetchResult(final_url=final_url, title=title, snippet=snippet, body=text)


class SecureFetcher:
    """Fetch a URL only after validating its scheme and host on every hop."""

    def __init__(
        self,
        *,
        allowed_schemes: Iterable[str],
        allowed_hosts: Iterable[str],
        max_hops: int = 5,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._schemes = frozenset(s.lower() for s in allowed_schemes)
        self._hosts = frozenset(allowed_hosts)
        self._max_hops = max_hops
        self._timeout = timeout
        self._transport = transport

    def _validate(self, url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme.lower() not in self._schemes:
            raise RejectionError("scheme")
        if (parts.hostname or "") not in self._hosts:
            raise RejectionError("host")

    def fetch(self, url: str) -> FetchResult:
        self._validate(url)
        current = url
        with httpx.Client(
            transport=self._transport, follow_redirects=False, timeout=self._timeout
        ) as client:
            for _ in range(self._max_hops + 1):
                response = client.get(current)
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise RejectionError("redirect")
                    target = urljoin(current, location)
                    # Re-validate the redirect target BEFORE contacting it, so a
                    # disallowed host is never reached on any hop. A hop failure is
                    # reported as the "redirect" class regardless of why it failed.
                    try:
                        self._validate(target)
                    except RejectionError:
                        raise RejectionError("redirect") from None
                    current = target
                    continue
                return parse_preview(str(response.url), response.text)
        raise RejectionError("redirect")
