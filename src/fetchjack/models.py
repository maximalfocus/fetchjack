"""Fictional Larkspur workspace and preview-record model.

Preview records are identified by UUID strings and are append-only: this module
provides no way to delete or mutate a stored record. An internal integer ``seq``
gives every record a stable insertion order so history is deterministic.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_uuid() -> str:
    """Return a fresh UUID string used as a preview record's public identity."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    """A fictional Larkspur workspace user authenticated by a demo-only token."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    token: Mapped[str] = mapped_column(String(128), unique=True)

    previews: Mapped[list[PreviewRecord]] = relationship(
        back_populates="owner", order_by="PreviewRecord.seq"
    )


class PreviewRecord(Base):
    """An append-only, UUID-identified link-preview record owned by one user."""

    __tablename__ = "preview_records"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=new_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    submitted_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(Text, default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")

    owner: Mapped[User] = relationship(back_populates="previews")
