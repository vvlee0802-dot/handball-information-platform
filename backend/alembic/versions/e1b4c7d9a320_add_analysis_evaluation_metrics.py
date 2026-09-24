"""add analysis evaluation metrics

Revision ID: e1b4c7d9a320
Revises: d9a2f7c4e681
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1b4c7d9a320"
down_revision: Union[str, Sequence[str], None] = "d9a2f7c4e681"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_tasks",
        sa.Column("evaluation_mode", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    for name in (
        "ground_truth_count",
        "true_positive_count",
        "false_positive_count",
        "false_negative_count",
    ):
        op.add_column(
            "analysis_tasks",
            sa.Column(name, sa.Integer(), server_default="0", nullable=False),
        )
    for name in ("precision", "recall", "f1", "mean_absolute_error_seconds"):
        op.add_column("analysis_tasks", sa.Column(name, sa.Float(), nullable=True))


def downgrade() -> None:
    for name in (
        "mean_absolute_error_seconds",
        "f1",
        "recall",
        "precision",
        "false_negative_count",
        "false_positive_count",
        "true_positive_count",
        "ground_truth_count",
        "evaluation_mode",
    ):
        op.drop_column("analysis_tasks", name)
