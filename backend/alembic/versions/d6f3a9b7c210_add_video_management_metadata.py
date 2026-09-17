"""add video management metadata

Revision ID: d6f3a9b7c210
Revises: b4e8f1a2c630
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6f3a9b7c210"
down_revision: Union[str, Sequence[str], None] = "b4e8f1a2c630"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("duration_seconds", sa.Float(), nullable=True))
    op.add_column(
        "videos",
        sa.Column("video_type", sa.String(30), server_default="original", nullable=False),
    )
    op.add_column("videos", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "video_upload_sessions",
        sa.Column("duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "video_upload_sessions",
        sa.Column("video_type", sa.String(30), server_default="original", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("video_upload_sessions", "video_type")
    op.drop_column("video_upload_sessions", "duration_seconds")
    op.drop_column("videos", "deleted_at")
    op.drop_column("videos", "video_type")
    op.drop_column("videos", "duration_seconds")
