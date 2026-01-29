from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


metadata_obj = MetaData()


class Base(DeclarativeBase):
    metadata = metadata_obj


# Import models here for Alembic to discover them
try:
    from app.models.batch import Batch  # noqa: F401  # pylint: disable=unused-import
    from app.models.workflow_node_version import WorkflowNodeVersion  # noqa: F401
    from app.models.workflow_template_step import (  # noqa: F401  # pylint: disable=unused-import
        WorkflowTemplateStep,
    )
except Exception:  # pragma: no cover - defensive for initial bootstrap
    Batch = None
    WorkflowNodeVersion = None
    WorkflowTemplateStep = None
