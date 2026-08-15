"""Append-only accessors for preview records.

Only two operations exist: append a record and list a user's records in
insertion order. There is deliberately no update or delete, so a stored preview
record can never be mutated or removed.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PreviewRecord, User


def add_preview_record(
    session: Session,
    *,
    owner: User,
    submitted_url: str,
    status: str,
    title: str = "",
    snippet: str = "",
    body: str = "",
) -> PreviewRecord:
    """Append one preview record for ``owner`` and return it."""
    record = PreviewRecord(
        owner_id=owner.id,
        submitted_url=submitted_url,
        status=status,
        title=title,
        snippet=snippet,
        body=body,
    )
    session.add(record)
    session.flush()
    return record


def list_preview_records(session: Session, *, owner: User) -> list[PreviewRecord]:
    """Return ``owner``'s preview records in stable insertion order."""
    stmt = (
        select(PreviewRecord).where(PreviewRecord.owner_id == owner.id).order_by(PreviewRecord.seq)
    )
    return list(session.scalars(stmt))
