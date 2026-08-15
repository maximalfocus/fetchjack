from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from fetchjack.db import create_database, make_session_factory


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    db_path = tmp_path / "fetchjack.db"
    engine = create_database(f"sqlite+pysqlite:///{db_path}")
    factory = make_session_factory(engine)
    with factory() as db_session:
        yield db_session
    engine.dispose()
