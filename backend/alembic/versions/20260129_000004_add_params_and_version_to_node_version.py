"""add params and version to workflow_node_version

Revision ID: 20260129_000004
Revises: 20260129_000003
Create Date: 2026-01-29 09:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260129_000004"
down_revision: Union[str, None] = "20260129_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflow_node_version",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "workflow_node_version",
        sa.Column("params", sa.JSON(), nullable=True),
    )

    # ensure existing rows have version 1
    op.execute("UPDATE workflow_node_version SET version = 1 WHERE version IS NULL")


def downgrade() -> None:
    op.drop_column("workflow_node_version", "params")
    op.drop_column("workflow_node_version", "version")
