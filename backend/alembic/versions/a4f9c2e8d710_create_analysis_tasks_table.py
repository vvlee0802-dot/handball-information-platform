"""create analysis tasks table

Revision ID: a4f9c2e8d710
Revises: 7e3b1a9c5d20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4f9c2e8d710"
down_revision: Union[str, Sequence[str], None] = "7e3b1a9c5d20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_tasks",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "task_type", sa.String(30), server_default="goal_detection", nullable=False
        ),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stage", sa.String(50), server_default="queued", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analysis_tasks_match_id"),
        "analysis_tasks",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_tasks_video_id"),
        "analysis_tasks",
        ["video_id"],
        unique=False,
    )
    op.create_index(
        "uq_analysis_tasks_active_video",
        "analysis_tasks",
        ["video_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_analysis_tasks_active_video", table_name="analysis_tasks")
    op.drop_index(op.f("ix_analysis_tasks_video_id"), table_name="analysis_tasks")
    op.drop_index(op.f("ix_analysis_tasks_match_id"), table_name="analysis_tasks")
    op.drop_table("analysis_tasks")
