"""create analysis predictions

Revision ID: f3a8d1e6c240
Revises: e1b4c7d9a320
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a8d1e6c240"
down_revision: Union[str, Sequence[str], None] = "e1b4c7d9a320"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_task_id", sa.String(36), nullable=False),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("predicted_timestamp_seconds", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("ground_truth_event_id", sa.Integer(), nullable=True),
        sa.Column("ground_truth_timestamp_seconds", sa.Float(), nullable=True),
        sa.Column("time_error_seconds", sa.Float(), nullable=True),
        sa.Column("training_decision", sa.String(20), server_default="pending", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_task_id"], ["analysis_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ground_truth_event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_predictions_analysis_task_id", "analysis_predictions", ["analysis_task_id"])
    op.create_index("ix_analysis_predictions_ground_truth_event_id", "analysis_predictions", ["ground_truth_event_id"])
    op.create_index("ix_analysis_predictions_task_outcome", "analysis_predictions", ["analysis_task_id", "outcome"])


def downgrade() -> None:
    op.drop_index("ix_analysis_predictions_task_outcome", table_name="analysis_predictions")
    op.drop_index("ix_analysis_predictions_ground_truth_event_id", table_name="analysis_predictions")
    op.drop_index("ix_analysis_predictions_analysis_task_id", table_name="analysis_predictions")
    op.drop_table("analysis_predictions")
