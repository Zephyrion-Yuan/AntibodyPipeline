"""create lineage_edge table

Revision ID: 20260129_000005
Revises: 20260129_000004
Create Date: 2026-01-29 10:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260129_000005"
down_revision: Union[str, None] = "20260129_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = sa.dialects.postgresql.UUID(as_uuid=True).with_variant(
        sa.String(length=36), "sqlite"
    )

    op.create_table(
        "lineage_edge",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("source_node_version_id", uuid_type, sa.ForeignKey("workflow_node_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_node_version_id", uuid_type, sa.ForeignKey("workflow_node_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("source_node_version_id", "target_node_version_id", "relation", name="uq_lineage_edge_unique_relation"),
    )


def downgrade() -> None:
    op.drop_table("lineage_edge")
