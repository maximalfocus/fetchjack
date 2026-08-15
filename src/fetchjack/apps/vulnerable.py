"""Vulnerable preview application entry point — intentionally unsafe.

This application performs NO scheme or host validation and follows redirects. It
exists only to demonstrate SSRF locally, and refuses to start unless the operator
has taken both deliberate opt-in actions (see ``fetchjack.gating``). Never deploy
it.
"""

from __future__ import annotations

import os

from fetchjack.config import DEMO_USERS, get_database_url
from fetchjack.fetching import VulnerableFetcher
from fetchjack.gating import require_demo_ack
from fetchjack.service import create_service_app

require_demo_ack(os.environ, app_name="vulnerable")

app = create_service_app(
    fetcher=VulnerableFetcher(),
    users=DEMO_USERS,
    database_url=get_database_url("sqlite+pysqlite:////app/var/vulnerable.db"),
)
