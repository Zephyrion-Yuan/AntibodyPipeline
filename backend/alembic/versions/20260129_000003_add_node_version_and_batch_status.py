"""add workflow_node_version table and batch status

Revision ID: 20260129_000003
Revises: 20260129_000002
Create Date: 2026-01-29 00:30:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260129_000003"
down_revision: Union[str, None] = "20260129_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = sa.dialects.postgresql.UUID(as_uuid=True).with_variant(
        sa.String(length=36), "sqlite"
    )

    op.add_column(
        "batch",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
    )

    op.create_table(
        "workflow_node_version",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("batch_id", uuid_type, sa.ForeignKey("batch.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_version", sa.String(length=32), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("step_index >= 1", name="ck_node_version_step_index_positive"),
    )


def downgrade() -> None:
    op.drop_table("workflow_node_version")
    op.drop_column("batch", "status")
