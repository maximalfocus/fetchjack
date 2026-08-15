"""Naive preview application entry point — intentionally half-fixed.

This application validates only the *submitted* URL against the allowlist and
then follows redirects without re-validating each hop, so an allowlisted host
that redirects to an internal target defeats it. It is gated exactly like the
vulnerable application and must never be deployed.
"""

from __future__ import annotations

import os

from fetchjack.config import (
    DEMO_USERS,
    get_allowed_hosts,
    get_allowed_schemes,
    get_database_url,
)
from fetchjack.fetching import NaiveFetcher
from fetchjack.gating import require_demo_ack
from fetchjack.service import create_service_app

require_demo_ack(os.environ, app_name="naive")

app = create_service_app(
    fetcher=NaiveFetcher(
        allowed_schemes=get_allowed_schemes(),
        allowed_hosts=get_allowed_hosts(),
    ),
    users=DEMO_USERS,
    database_url=get_database_url("sqlite+pysqlite:////app/var/naive.db"),
)
