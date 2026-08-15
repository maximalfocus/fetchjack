"""The container network must not reach the public internet.

Runs inside the gate, where the network blocks egress. Attempts to reach public
hosts (by name and by raw IP) must fail — the vulnerable application's safety in
later slices depends on this network-level guarantee.
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.parametrize("target", ["http://example.com", "http://1.1.1.1"])
def test_no_public_internet_egress(target: str) -> None:
    with pytest.raises(httpx.HTTPError):
        httpx.get(target, timeout=3.0)
