"""create players table

Revision ID: 6a5f1c8d92b4
Revises: 3d7c9f02b1ae
Create Date: 2026-09-16 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6a5f1c8d92b4"
down_revision: Union[str, Sequence[str], None] = "3d7c9f02b1ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(length=50), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "number", name="uq_players_team_number"),
    )
    op.create_index(op.f("ix_players_team_id"), "players", ["team_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_players_team_id"), table_name="players")
    op.drop_table("players")
