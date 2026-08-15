from __future__ import annotations

import pytest

from fetchjack.gating import require_demo_ack


def test_refuses_without_acknowledgement() -> None:
    with pytest.raises(RuntimeError, match="Refusing to start"):
        require_demo_ack({}, app_name="vulnerable")


def test_refuses_with_wrong_acknowledgement() -> None:
    with pytest.raises(RuntimeError):
        require_demo_ack({"ALLOW_VULNERABLE_DEMO": "1"}, app_name="vulnerable")


def test_allows_with_exact_acknowledgement() -> None:
    require_demo_ack({"ALLOW_VULNERABLE_DEMO": "true"}, app_name="vulnerable")
