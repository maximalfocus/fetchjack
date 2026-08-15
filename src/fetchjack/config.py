"""Demo configuration: fictional users and the secure allowlist defaults.

These bearer tokens are unmistakably demo-only and grant access to nothing but
this local demonstration's fictional preview history.
"""

from __future__ import annotations

import os

DEMO_USERS: dict[str, str] = {
    "demo-token-ada": "ada",
    "demo-token-grace": "grace",
}


def get_allowed_schemes() -> tuple[str, ...]:
    raw = os.environ.get("ALLOWED_SCHEMES", "http,https")
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def get_allowed_hosts() -> tuple[str, ...]:
    raw = os.environ.get("ALLOWED_HOSTS", "assets.larkspur.test")
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def get_database_url(default: str) -> str:
    return os.environ.get("DATABASE_URL", default)
