"""add rag evaluations

Revision ID: d7a4f2c8e130
Revises: c5e8a1d7f940
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7a4f2c8e130"
down_revision: Union[str, Sequence[str], None] = "c5e8a1d7f940"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_evaluation_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_document_ids", sa.JSON(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_evaluation_cases_owner_user_id", "rag_evaluation_cases", ["owner_user_id"])
    op.create_index("ix_rag_evaluation_cases_team_id", "rag_evaluation_cases", ["team_id"])
    op.create_index("ix_rag_evaluation_cases_is_active", "rag_evaluation_cases", ["is_active"])
    op.create_table(
        "rag_evaluation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_by_user_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("answer_model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("relevance_threshold", sa.Float(), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False),
        sa.Column("recall_at_k", sa.Float(), nullable=False),
        sa.Column("citation_hit_rate", sa.Float(), nullable=False),
        sa.Column("ungrounded_answer_rate", sa.Float(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_evaluation_runs_run_by_user_id", "rag_evaluation_runs", ["run_by_user_id"])
    op.create_index("ix_rag_evaluation_runs_team_id", "rag_evaluation_runs", ["team_id"])
    op.create_index("ix_rag_evaluation_runs_created_at", "rag_evaluation_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_rag_evaluation_runs_created_at", table_name="rag_evaluation_runs")
    op.drop_index("ix_rag_evaluation_runs_team_id", table_name="rag_evaluation_runs")
    op.drop_index("ix_rag_evaluation_runs_run_by_user_id", table_name="rag_evaluation_runs")
    op.drop_table("rag_evaluation_runs")
    op.drop_index("ix_rag_evaluation_cases_is_active", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_team_id", table_name="rag_evaluation_cases")
    op.drop_index("ix_rag_evaluation_cases_owner_user_id", table_name="rag_evaluation_cases")
    op.drop_table("rag_evaluation_cases")
