"""add resumable video uploads

Revision ID: b4e8f1a2c630
Revises: a7c9d2e5f130
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e8f1a2c630"
down_revision: Union[str, Sequence[str], None] = "a7c9d2e5f130"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_upload_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("total_size", sa.BigInteger(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("total_parts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="uploading", nullable=False),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("video_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_upload_sessions_match_id", "video_upload_sessions", ["match_id"])
    op.create_index("ix_video_upload_sessions_user_id", "video_upload_sessions", ["user_id"])
    op.create_index("ix_video_upload_sessions_fingerprint", "video_upload_sessions", ["fingerprint"])
    op.create_table(
        "video_upload_parts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("upload_id", sa.String(36), nullable=False),
        sa.Column("part_number", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["upload_id"], ["video_upload_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("upload_id", "part_number", name="uq_video_upload_part_number"),
    )
    op.create_index("ix_video_upload_parts_upload_id", "video_upload_parts", ["upload_id"])


def downgrade() -> None:
    op.drop_index("ix_video_upload_parts_upload_id", table_name="video_upload_parts")
    op.drop_table("video_upload_parts")
    op.drop_index("ix_video_upload_sessions_fingerprint", table_name="video_upload_sessions")
    op.drop_index("ix_video_upload_sessions_user_id", table_name="video_upload_sessions")
    op.drop_index("ix_video_upload_sessions_match_id", table_name="video_upload_sessions")
    op.drop_table("video_upload_sessions")
