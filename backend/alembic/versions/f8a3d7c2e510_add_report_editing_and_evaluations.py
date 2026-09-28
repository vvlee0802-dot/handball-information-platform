"""add report editing and evaluations

Revision ID: f8a3d7c2e510
Revises: e7c2a9f4b610
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a3d7c2e510"
down_revision: Union[str, Sequence[str], None] = "e7c2a9f4b610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_match_reports",
        sa.Column("generation_focus", sa.String(length=30), server_default="full_match", nullable=False),
    )
    op.add_column(
        "ai_match_reports",
        sa.Column("detail_level", sa.String(length=20), server_default="concise", nullable=False),
    )
    op.add_column("ai_match_reports", sa.Column("user_output_data", sa.JSON(), nullable=True))
    op.add_column("ai_match_reports", sa.Column("edited_by_user_id", sa.Integer(), nullable=True))
    op.add_column("ai_match_reports", sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "ai_match_reports",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_foreign_key(
        "fk_ai_match_reports_edited_by_user_id_users",
        "ai_match_reports",
        "users",
        ["edited_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_ai_match_reports_edited_by_user_id",
        "ai_match_reports",
        ["edited_by_user_id"],
    )
    op.create_table(
        "ai_report_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("evaluated_by_user_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["evaluated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["ai_match_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_report_evaluations_report_id", "ai_report_evaluations", ["report_id"])
    op.create_index("ix_ai_report_evaluations_match_id", "ai_report_evaluations", ["match_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_report_evaluations_match_id", table_name="ai_report_evaluations")
    op.drop_index("ix_ai_report_evaluations_report_id", table_name="ai_report_evaluations")
    op.drop_table("ai_report_evaluations")
    op.drop_index("ix_ai_match_reports_edited_by_user_id", table_name="ai_match_reports")
    op.drop_constraint(
        "fk_ai_match_reports_edited_by_user_id_users",
        "ai_match_reports",
        type_="foreignkey",
    )
    op.drop_column("ai_match_reports", "updated_at")
    op.drop_column("ai_match_reports", "edited_at")
    op.drop_column("ai_match_reports", "edited_by_user_id")
    op.drop_column("ai_match_reports", "user_output_data")
    op.drop_column("ai_match_reports", "detail_level")
    op.drop_column("ai_match_reports", "generation_focus")
