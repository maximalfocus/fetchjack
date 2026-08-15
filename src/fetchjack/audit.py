"""Structured rejection audit events.

A rejected submission emits exactly one JSON line to standard output. The event
carries enough to correlate and attribute the attempt, but never the fetched
content, fixture-file contents, the internal credential, bearer tokens, or
authorization headers. The submitted URL is included only as a length-capped,
control-character-escaped rendering.
"""

from __future__ import annotations

import json
import sys

_MAX_URL_LEN = 200


def emit_rejection_event(
    *,
    request_id: str,
    user: str,
    action: str,
    rejection_class: str,
    submitted_url: str,
) -> None:
    event = {
        "event": "preview_rejected",
        "request_id": request_id,
        "user": user,
        "action": action,
        "rejection_class": rejection_class,
        "outcome": "rejected",
        # json.dumps(ensure_ascii=True) escapes control and non-ASCII characters.
        "submitted_url": submitted_url[:_MAX_URL_LEN],
    }
    sys.stdout.write(json.dumps(event, sort_keys=True) + "\n")
    sys.stdout.flush()
