"""add construct target to lineage edges

Revision ID: 20260129_000009
Revises: 20260129_000008
Create Date: 2026-01-29 11:45:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260129_000009"
down_revision: Union[str, None] = "20260129_000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = sa.dialects.postgresql.UUID(as_uuid=True).with_variant(
        sa.String(length=36), "sqlite"
    )
    op.add_column("lineage_edge", sa.Column("target_construct_id", uuid_type, nullable=True))
    op.create_foreign_key(
        "fk_lineage_edge_construct",
        "lineage_edge",
        "construct",
        ["target_construct_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_lineage_edge_construct", "lineage_edge", type_="foreignkey")
    op.drop_column("lineage_edge", "target_construct_id")
