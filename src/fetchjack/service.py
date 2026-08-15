"""Shared preview service layer.

One factory builds a FastAPI application parameterised by a ``Fetcher``. The
secure, vulnerable, and naive applications differ only in the fetcher they pass;
authentication, the preview lifecycle, storage, and audit are identical.
"""

# NOTE: deliberately no ``from __future__ import annotations`` here. The route
# dependencies (``authenticate``, ``get_db``) are closures defined inside
# ``create_service_app``; FastAPI must evaluate ``Annotated[..., Depends(...)]``
# eagerly while those names are in scope, which stringized annotations prevent.

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import emit_rejection_event
from .db import create_database, make_session_factory
from .fetching import Fetcher, RejectionError
from .models import User
from .store import add_preview_record, list_preview_records

_GENERIC_400 = {"error": "request rejected"}
_CHALLENGE = {"WWW-Authenticate": "Bearer"}


class PreviewRequest(BaseModel):
    url: str


class PreviewResponse(BaseModel):
    id: str
    submitted_url: str
    status: str
    title: str
    snippet: str
    body: str


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


def create_service_app(*, fetcher: Fetcher, users: dict[str, str], database_url: str) -> FastAPI:
    engine = create_database(database_url)
    session_factory = make_session_factory(engine)

    # Seed the fictional demo users deterministically.
    with session_factory() as seed:
        existing = {user.token for user in seed.scalars(select(User)).all()}
        for token, username in users.items():
            if token not in existing:
                seed.add(User(username=username, token=token))
        seed.commit()

    app = FastAPI(title="fetchjack")

    def get_db() -> Iterator[Session]:
        with session_factory() as db:
            yield db

    def authenticate(
        db: Annotated[Session, Depends(get_db)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> User:
        token = _bearer_token(authorization)
        user = None
        if token is not None:
            user = db.scalars(select(User).where(User.token == token)).first()
        if user is None:
            raise HTTPException(status_code=401, detail="unauthorized", headers=_CHALLENGE)
        return user

    @app.get("/healthz")
    def healthz() -> Response:
        return JSONResponse(content={"status": "ok"})

    @app.post("/previews")
    def create_preview(
        payload: PreviewRequest,
        request: Request,
        user: Annotated[User, Depends(authenticate)],
        db: Annotated[Session, Depends(get_db)],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        try:
            result = fetcher.fetch(payload.url)
        except RejectionError as exc:
            emit_rejection_event(
                request_id=request_id,
                user=user.username,
                action="POST /previews",
                rejection_class=exc.rejection_class,
                submitted_url=payload.url,
            )
            return JSONResponse(status_code=400, content=_GENERIC_400)
        record = add_preview_record(
            db,
            owner=user,
            submitted_url=payload.url,
            status="ok",
            title=result.title,
            snippet=result.snippet,
            body=result.body,
        )
        db.commit()
        body = PreviewResponse(
            id=record.id,
            submitted_url=record.submitted_url,
            status=record.status,
            title=record.title,
            snippet=record.snippet,
            body=record.body,
        )
        return JSONResponse(status_code=201, content=body.model_dump())

    @app.get("/previews")
    def list_previews(
        user: Annotated[User, Depends(authenticate)],
        db: Annotated[Session, Depends(get_db)],
    ) -> Response:
        records = list_preview_records(db, owner=user)
        payload = [
            PreviewResponse(
                id=record.id,
                submitted_url=record.submitted_url,
                status=record.status,
                title=record.title,
                snippet=record.snippet,
                body=record.body,
            ).model_dump()
            for record in records
        ]
        return JSONResponse(content=payload)

    return app
