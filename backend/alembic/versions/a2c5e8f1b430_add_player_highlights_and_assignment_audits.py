"""add player highlights and assignment audits

Revision ID: a2c5e8f1b430
Revises: f3a8d1e6c240
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2c5e8f1b430"
down_revision: Union[str, Sequence[str], None] = "f3a8d1e6c240"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clip_exports",
        sa.Column("export_type", sa.String(length=30), server_default="event_clips", nullable=False),
    )
    op.add_column("clip_exports", sa.Column("player_id", sa.Integer(), nullable=True))
    op.add_column("clip_exports", sa.Column("event_types", sa.String(length=255), nullable=True))
    op.create_index("ix_clip_exports_player_id", "clip_exports", ["player_id"], unique=False)
    op.create_foreign_key(
        "fk_clip_exports_player_id_players",
        "clip_exports",
        "players",
        ["player_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "event_player_assignment_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("old_player_id", sa.Integer(), nullable=True),
        sa.Column("old_player_name", sa.String(length=120), nullable=True),
        sa.Column("new_player_id", sa.Integer(), nullable=False),
        sa.Column("new_player_name", sa.String(length=120), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_name", sa.String(length=120), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_player_assignment_audits_match_id",
        "event_player_assignment_audits",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_player_assignment_audits_event_id",
        "event_player_assignment_audits",
        ["event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_player_assignment_audits_event_id", table_name="event_player_assignment_audits")
    op.drop_index("ix_event_player_assignment_audits_match_id", table_name="event_player_assignment_audits")
    op.drop_table("event_player_assignment_audits")
    op.drop_constraint("fk_clip_exports_player_id_players", "clip_exports", type_="foreignkey")
    op.drop_index("ix_clip_exports_player_id", table_name="clip_exports")
    op.drop_column("clip_exports", "event_types")
    op.drop_column("clip_exports", "player_id")
    op.drop_column("clip_exports", "export_type")
