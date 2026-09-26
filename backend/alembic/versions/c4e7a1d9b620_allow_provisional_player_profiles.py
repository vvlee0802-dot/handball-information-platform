"""allow provisional player profiles

Revision ID: c4e7a1d9b620
Revises: b7d4e9a1c260
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e7a1d9b620"
down_revision: Union[str, Sequence[str], None] = "b7d4e9a1c260"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "players",
        "position",
        existing_type=sa.String(length=50),
        nullable=True,
    )
    op.alter_column(
        "players",
        "birth_date",
        existing_type=sa.Date(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        "UPDATE players SET position = '待完善' WHERE position IS NULL"
    )
    op.execute(
        "UPDATE players SET birth_date = DATE '1900-01-01' WHERE birth_date IS NULL"
    )
    op.alter_column(
        "players",
        "birth_date",
        existing_type=sa.Date(),
        nullable=False,
    )
    op.alter_column(
        "players",
        "position",
        existing_type=sa.String(length=50),
        nullable=False,
    )
