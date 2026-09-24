"""add AI candidate metadata

Revision ID: c6d8f1a3b520
Revises: a4f9c2e8d710
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6d8f1a3b520"
down_revision: Union[str, Sequence[str], None] = "a4f9c2e8d710"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_tasks", sa.Column("model_version", sa.String(120), nullable=True)
    )
    op.add_column(
        "analysis_tasks",
        sa.Column("candidate_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("events", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("model_version", sa.String(120), nullable=True))
    op.add_column("events", sa.Column("analysis_task_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_events_analysis_task_id",
        "events",
        "analysis_tasks",
        ["analysis_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_events_analysis_task_id"),
        "events",
        ["analysis_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_events_analysis_task_id"), table_name="events")
    op.drop_constraint("fk_events_analysis_task_id", "events", type_="foreignkey")
    op.drop_column("events", "analysis_task_id")
    op.drop_column("events", "model_version")
    op.drop_column("events", "confidence")
    op.drop_column("analysis_tasks", "candidate_count")
    op.drop_column("analysis_tasks", "model_version")
