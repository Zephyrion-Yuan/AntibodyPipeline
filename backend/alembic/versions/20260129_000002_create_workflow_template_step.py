"""create workflow_template_step table and seed v1

Revision ID: 20260129_000002
Revises: 20260129_000001
Create Date: 2026-01-29 00:10:00
"""
from typing import Sequence, Union
import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260129_000002"
down_revision: Union[str, None] = "20260129_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = sa.dialects.postgresql.UUID(as_uuid=True).with_variant(
        sa.String(length=36), "sqlite"
    )

    op.create_table(
        "workflow_template_step",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("template_version", sa.String(length=32), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "template_version", "step_index", name="uq_template_step_version_index"
        ),
        sa.CheckConstraint("step_index >= 1", name="ck_step_index_positive"),
    )

    steps = [
        {
            "id": str(uuid.uuid4()),
            "template_version": "v1",
            "step_index": 1,
            "name": "Step 1",
            "description": "Initial step",
        },
        {
            "id": str(uuid.uuid4()),
            "template_version": "v1",
            "step_index": 2,
            "name": "Step 2",
            "description": "Middle step",
        },
        {
            "id": str(uuid.uuid4()),
            "template_version": "v1",
            "step_index": 3,
            "name": "Step 3",
            "description": "Final step",
        },
    ]
    op.bulk_insert(sa.table(
        "workflow_template_step",
        sa.column("id", uuid_type),
        sa.column("template_version", sa.String(length=32)),
        sa.column("step_index", sa.Integer()),
        sa.column("name", sa.String(length=255)),
        sa.column("description", sa.Text()),
    ), steps)


def downgrade() -> None:
    op.drop_table("workflow_template_step")
