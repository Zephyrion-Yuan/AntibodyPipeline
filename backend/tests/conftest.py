import os
import pathlib
import sys
from typing import Generator

import pytest
from sqlalchemy.orm import Session

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure tests run against an isolated SQLite database
os.environ.setdefault("APP_DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.db.base import Base  # noqa: E402  pylint: disable=wrong-import-position
from app.db.session import SessionLocal, engine  # noqa: E402  pylint: disable=wrong-import-position
from app.models.workflow_template_step import (  # noqa: E402  pylint: disable=wrong-import-position
    WorkflowTemplateStep,
)


@pytest.fixture(scope="session", autouse=True)
def create_test_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    _seed_template_steps()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    # isolate each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed_template_steps()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_template_steps() -> None:
    session = SessionLocal()
    try:
        has_steps = session.query(WorkflowTemplateStep).count() > 0
        if not has_steps:
            steps = [
                WorkflowTemplateStep(template_version="v1", step_index=1, name="Step 1"),
                WorkflowTemplateStep(template_version="v1", step_index=2, name="Step 2"),
                WorkflowTemplateStep(template_version="v1", step_index=3, name="Step 3"),
            ]
            session.add_all(steps)
            session.commit()
    finally:
        session.close()
