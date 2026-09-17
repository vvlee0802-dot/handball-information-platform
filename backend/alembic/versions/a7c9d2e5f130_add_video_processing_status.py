"""add video processing status

Revision ID: a7c9d2e5f130
Revises: f6a8b1d4c920
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c9d2e5f130"
down_revision: Union[str, Sequence[str], None] = "f6a8b1d4c920"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column("processing_status", sa.String(20), server_default="queued", nullable=False),
    )
    op.add_column(
        "videos",
        sa.Column("processing_progress", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "videos",
        sa.Column("processing_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("videos", sa.Column("failure_reason", sa.String(500), nullable=True))
    op.add_column("videos", sa.Column("checksum_sha256", sa.String(64), nullable=True))
    op.add_column(
        "videos",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE videos SET processing_status = 'completed', "
        "processing_progress = 100, processing_completed_at = now()"
    )


def downgrade() -> None:
    op.drop_column("videos", "processing_completed_at")
    op.drop_column("videos", "processing_started_at")
    op.drop_column("videos", "checksum_sha256")
    op.drop_column("videos", "failure_reason")
    op.drop_column("videos", "processing_attempts")
    op.drop_column("videos", "processing_progress")
    op.drop_column("videos", "processing_status")
