"""create chain table

Revision ID: 20260129_000007
Revises: 20260129_000006
Create Date: 2026-01-29 10:40:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260129_000007"
down_revision: Union[str, None] = "20260129_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = sa.dialects.postgresql.UUID(as_uuid=True).with_variant(
        sa.String(length=36), "sqlite"
    )

    op.create_table(
        "chain",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column(
            "node_version_id",
            uuid_type,
            sa.ForeignKey("workflow_node_version.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("sequence", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("chain")
