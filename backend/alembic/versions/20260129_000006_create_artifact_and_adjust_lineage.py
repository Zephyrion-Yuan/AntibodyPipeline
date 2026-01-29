"""create artifact table and adjust lineage

Revision ID: 20260129_000006
Revises: 20260129_000005
Create Date: 2026-01-29 10:20:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260129_000006"
down_revision: Union[str, None] = "20260129_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = sa.dialects.postgresql.UUID(as_uuid=True).with_variant(
        sa.String(length=36), "sqlite"
    )

    op.create_table(
        "artifact",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column(
            "node_version_id",
            uuid_type,
            sa.ForeignKey("workflow_node_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False, server_default="text/plain"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Adjust lineage_edge to allow artifact targets
    op.add_column("lineage_edge", sa.Column("target_artifact_id", uuid_type, nullable=True))
    op.create_foreign_key(
        "fk_lineage_edge_target_artifact",
        "lineage_edge",
        "artifact",
        ["target_artifact_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_lineage_edge_target_artifact", "lineage_edge", type_="foreignkey")
    op.drop_column("lineage_edge", "target_artifact_id")
    op.drop_table("artifact")
