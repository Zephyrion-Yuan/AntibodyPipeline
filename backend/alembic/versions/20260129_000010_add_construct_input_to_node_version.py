"""add construct input reference to workflow_node_version

Revision ID: 20260129_000010
Revises: 20260129_000009
Create Date: 2026-01-29 15:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260129_000010"
down_revision: Union[str, None] = "20260129_000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = sa.dialects.postgresql.UUID(as_uuid=True).with_variant(
        sa.String(length=36), "sqlite"
    )
    op.add_column(
        "workflow_node_version",
        sa.Column("input_construct_id", uuid_type, nullable=True),
    )
    op.create_foreign_key(
        "fk_node_version_input_construct",
        "workflow_node_version",
        "construct",
        ["input_construct_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_node_version_input_construct",
        "workflow_node_version",
        type_="foreignkey",
    )
    op.drop_column("workflow_node_version", "input_construct_id")
