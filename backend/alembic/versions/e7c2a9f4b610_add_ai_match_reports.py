"""add ai match reports

Revision ID: e7c2a9f4b610
Revises: c4e7a1d9b620
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e7c2a9f4b610"
down_revision: Union[str, Sequence[str], None] = "c4e7a1d9b620"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_match_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("generated_by_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("output_data", sa.JSON(), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_match_reports_match_id", "ai_match_reports", ["match_id"])
    op.create_index(
        "ix_ai_match_reports_generated_by_user_id",
        "ai_match_reports",
        ["generated_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_match_reports_generated_by_user_id", table_name="ai_match_reports")
    op.drop_index("ix_ai_match_reports_match_id", table_name="ai_match_reports")
    op.drop_table("ai_match_reports")
