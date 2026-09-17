"""create clip export tables

Revision ID: 7e3b1a9c5d20
Revises: f2c4a8d9e710
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7e3b1a9c5d20"
down_revision: Union[str, Sequence[str], None] = "f2c4a8d9e710"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clip_exports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_clip_exports_match_id"), "clip_exports", ["match_id"], unique=False
    )
    op.create_table(
        "clip_export_events",
        sa.Column("clip_export_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["clip_export_id"], ["clip_exports.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("clip_export_id", "event_id"),
    )


def downgrade() -> None:
    op.drop_table("clip_export_events")
    op.drop_index(op.f("ix_clip_exports_match_id"), table_name="clip_exports")
    op.drop_table("clip_exports")
