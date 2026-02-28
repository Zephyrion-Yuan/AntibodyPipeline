import pytest

from app import statuses
from app.models import Artifact, Batch, WorkflowNodeVersion, WorkflowTemplateStep
from app.activities.step_activities import execute_step


def test_artifact_fields_unchanged_after_creation(db_session):
    """Artifact uri and content_type should remain stable after creation."""
    batch = Batch(name="Immutability Batch")
    db_session.add(batch)
    db_session.commit()

    nv = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        version=1,
        status=statuses.IDLE,
    )
    db_session.add(nv)
    db_session.commit()

    execute_step(batch.id, 1, nv.id)

    db_session.expire_all()
    artifact = db_session.query(Artifact).filter(Artifact.node_version_id == nv.id).one()
    original_uri = artifact.uri
    original_content_type = artifact.content_type

    # Re-read after expiry to confirm persistence
    db_session.expire_all()
    artifact = db_session.get(Artifact, artifact.id)
    assert artifact.uri == original_uri
    assert artifact.content_type == original_content_type


def test_template_step_index_uniqueness(db_session):
    """Template step_index + template_version must be unique (enforced by constraint)."""
    from sqlalchemy.exc import IntegrityError

    duplicate = WorkflowTemplateStep(
        template_version="v1",
        step_index=1,
        name="Duplicate Step 1",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_completed_node_version_not_re_executed(db_session):
    """Re-running execute_step on a completed node version is a no-op."""
    batch = Batch(name="Immutability Batch 2")
    db_session.add(batch)
    db_session.commit()

    nv = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        version=1,
        status=statuses.IDLE,
    )
    db_session.add(nv)
    db_session.commit()

    uri_first = execute_step(batch.id, 1, nv.id)

    db_session.expire_all()
    nv = db_session.get(WorkflowNodeVersion, nv.id)
    assert nv.status == statuses.COMPLETED
    original_artifact_uri = nv.artifact_uri

    # Second execution should be a no-op
    uri_second = execute_step(batch.id, 1, nv.id)
    assert uri_second == original_artifact_uri

    db_session.expire_all()
    nv = db_session.get(WorkflowNodeVersion, nv.id)
    assert nv.status == statuses.COMPLETED
    assert nv.artifact_uri == original_artifact_uri
