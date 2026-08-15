from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

import fetchjack.store as store_mod
from fetchjack.models import User
from fetchjack.store import add_preview_record, list_preview_records


def _make_user(session: Session, username: str, token: str) -> User:
    user = User(username=username, token=token)
    session.add(user)
    session.flush()
    return user


def test_preview_records_are_uuid_identified(session: Session) -> None:
    user = _make_user(session, "ada", "demo-token-ada")
    record = add_preview_record(
        session,
        owner=user,
        submitted_url="http://assets.larkspur.test/notes/1",
        status="ok",
    )
    assert str(uuid.UUID(record.id)) == record.id


def test_preview_history_is_append_only_and_ordered(session: Session) -> None:
    user = _make_user(session, "grace", "demo-token-grace")
    urls = [f"http://assets.larkspur.test/notes/{i}" for i in range(1, 6)]
    created = [add_preview_record(session, owner=user, submitted_url=u, status="ok") for u in urls]

    listed = list_preview_records(session, owner=user)
    assert [r.submitted_url for r in listed] == urls
    assert [r.id for r in listed] == [r.id for r in created]

    # The store exposes only append + list: no delete/mutate operation exists.
    forbidden = ("delete", "remove", "update", "mutate", "drop")
    assert not any(name.startswith(forbidden) for name in dir(store_mod))


def test_same_url_creates_independent_records(session: Session) -> None:
    user = _make_user(session, "linus", "demo-token-linus")
    url = "http://assets.larkspur.test/notes/1"
    first = add_preview_record(session, owner=user, submitted_url=url, status="ok")
    second = add_preview_record(session, owner=user, submitted_url=url, status="ok")
    assert first.id != second.id
    assert len(list_preview_records(session, owner=user)) == 2


def test_history_is_scoped_per_user(session: Session) -> None:
    alice = _make_user(session, "alice", "demo-token-alice")
    bob = _make_user(session, "bob", "demo-token-bob")
    add_preview_record(
        session,
        owner=alice,
        submitted_url="http://assets.larkspur.test/notes/1",
        status="ok",
    )
    assert len(list_preview_records(session, owner=alice)) == 1
    assert len(list_preview_records(session, owner=bob)) == 0
