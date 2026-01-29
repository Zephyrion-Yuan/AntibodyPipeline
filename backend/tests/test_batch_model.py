from sqlalchemy import select

from app.models import Batch


def test_create_and_query_batch(db_session):
    batch = Batch(name="Test Batch", description="Initial batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    fetched = db_session.scalars(select(Batch).where(Batch.id == batch.id)).one()

    assert fetched.id == batch.id
    assert fetched.name == "Test Batch"
    assert fetched.description == "Initial batch"
    assert fetched.created_at is not None
    assert fetched.updated_at is not None
