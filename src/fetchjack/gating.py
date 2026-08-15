"""Two-action opt-in gate for the intentionally unsafe applications.

A non-secure application starts only when the operator has taken both deliberate
actions: enabling the ``vulnerable`` Compose profile (which decides whether the
service is created at all) and setting ``ALLOW_VULNERABLE_DEMO=true`` (checked
here). Either one alone is insufficient.
"""

from __future__ import annotations

from collections.abc import Mapping

ACK_ENV_VAR = "ALLOW_VULNERABLE_DEMO"


def require_demo_ack(env: Mapping[str, str], *, app_name: str) -> None:
    if env.get(ACK_ENV_VAR) != "true":
        raise RuntimeError(
            f"Refusing to start the intentionally vulnerable '{app_name}' application: it has no "
            "SSRF protection and is local educational code only. Start it deliberately by both "
            f"(1) enabling the 'vulnerable' Compose profile and (2) setting {ACK_ENV_VAR}=true."
        )
