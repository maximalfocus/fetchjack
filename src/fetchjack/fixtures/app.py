"""Deterministic in-network fixture HTTP service.

One image serves two roles selected by the ``FIXTURE_ROLE`` environment
variable:

* ``assets``   — the allowlisted upstream ``assets.larkspur.test``: benign
  preview content at ``/notes/{n}`` and a redirect endpoint ``/r?to=...``.
* ``internal`` — the non-allowlisted ``backoffice.larkspur.internal``: a
  conspicuously fictional internal service credential at ``/service-account``.

Every response depends only on the request — no clock, no randomness — so
identical requests always produce identical bytes.
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, Response

_HEALTH_JSON = json.dumps({"status": "ok"}) + "\n"

_INTERNAL_CREDENTIAL = (
    json.dumps(
        {
            "disclaimer": (
                "FICTIONAL DEMO FIXTURE - not a real credential; grants access to nothing."
            ),
            "fictional": True,
            "service": "larkspur-backoffice",
            "service_account_token": "fixture-internal-service-account-not-a-secret",
        },
        indent=2,
        sort_keys=True,
    )
    + "\n"
)


def _note_body(n: int) -> str:
    return (
        "<!doctype html>\n"
        f"<html><head><title>Larkspur note {n}</title></head>\n"
        f"<body><h1>Larkspur note {n}</h1>\n"
        f"<p>Fictional preview body for note {n}. Wholly invented demo content.</p>\n"
        "</body></html>\n"
    )


def create_app(role: str) -> FastAPI:
    """Build the fixture application for the given ``role``."""
    app = FastAPI(title=f"larkspur-fixture-{role}")

    @app.get("/healthz")
    def healthz() -> Response:
        return Response(content=_HEALTH_JSON, media_type="application/json")

    if role == "assets":

        @app.get("/notes/{n}")
        def notes(n: int) -> Response:
            return Response(content=_note_body(n), media_type="text/html; charset=utf-8")

        @app.get("/r")
        def redirect(to: str) -> Response:
            return Response(status_code=302, headers={"location": to})

    elif role == "internal":

        @app.get("/service-account")
        def service_account() -> Response:
            return Response(content=_INTERNAL_CREDENTIAL, media_type="application/json")

    else:
        raise RuntimeError(f"unknown FIXTURE_ROLE: {role!r}")

    return app


app = create_app(os.environ.get("FIXTURE_ROLE", "assets"))
