"""Secure preview application entry point.

The secure application is the default long-running Compose service. It enforces
a scheme and host allowlist on every request the server makes, including each
redirect hop.
"""

from __future__ import annotations

from fetchjack.config import (
    DEMO_USERS,
    get_allowed_hosts,
    get_allowed_schemes,
    get_database_url,
)
from fetchjack.fetching import SecureFetcher
from fetchjack.service import create_service_app

fetcher = SecureFetcher(
    allowed_schemes=get_allowed_schemes(),
    allowed_hosts=get_allowed_hosts(),
)

app = create_service_app(
    fetcher=fetcher,
    users=DEMO_USERS,
    database_url=get_database_url("sqlite+pysqlite:////app/var/secure.db"),
)
