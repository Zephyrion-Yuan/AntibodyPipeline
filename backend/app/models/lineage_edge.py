import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import GUID


class LineageEdge(Base):
    __tablename__ = "lineage_edge"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    source_node_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workflow_node_version.id", ondelete="CASCADE"), nullable=False
    )
    target_node_version_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("workflow_node_version.id", ondelete="CASCADE"), nullable=True
    )
    target_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("artifact.id", ondelete="CASCADE"), nullable=True
    )
    target_construct_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("construct.id", ondelete="CASCADE"), nullable=True
    )
    relation: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
