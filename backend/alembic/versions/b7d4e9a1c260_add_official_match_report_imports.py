"""add official match report imports

Revision ID: b7d4e9a1c260
Revises: a2c5e8f1b430
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d4e9a1c260"
down_revision: Union[str, Sequence[str], None] = "a2c5e8f1b430"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_report_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("parsed_data", sa.JSON(), nullable=False),
        sa.Column("conflicts", sa.JSON(), nullable=False),
        sa.Column("team_a_team_id", sa.Integer(), nullable=True),
        sa.Column("team_b_team_id", sa.Integer(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["team_a_team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["team_b_team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", "checksum_sha256", name="uq_match_report_match_checksum"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_match_report_imports_match_id", "match_report_imports", ["match_id"])
    op.create_index(
        "ix_match_report_imports_uploaded_by_user_id",
        "match_report_imports",
        ["uploaded_by_user_id"],
    )

    op.create_table(
        "official_team_match_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_import_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("report_side", sa.String(length=1), nullable=False),
        sa.Column("half_time_score", sa.Integer(), nullable=False),
        sa.Column("final_score", sa.Integer(), nullable=False),
        sa.Column("seven_meter_goals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("seven_meter_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("timeouts", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["report_import_id"], ["match_report_imports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_import_id", "team_id", name="uq_official_team_stat_report_team"),
    )
    op.create_index("ix_official_team_match_stats_report_import_id", "official_team_match_stats", ["report_import_id"])
    op.create_index("ix_official_team_match_stats_match_id", "official_team_match_stats", ["match_id"])
    op.create_index("ix_official_team_match_stats_team_id", "official_team_match_stats", ["team_id"])

    op.create_table(
        "official_player_match_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_import_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.String(length=120), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("goals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("yellow_cards", sa.Integer(), server_default="0", nullable=False),
        sa.Column("suspensions_2min", sa.Integer(), server_default="0", nullable=False),
        sa.Column("red_cards", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blue_cards", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["report_import_id"], ["match_report_imports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_import_id",
            "team_id",
            "number",
            name="uq_official_player_stat_report_team_number",
        ),
    )
    op.create_index("ix_official_player_match_stats_report_import_id", "official_player_match_stats", ["report_import_id"])
    op.create_index("ix_official_player_match_stats_match_id", "official_player_match_stats", ["match_id"])
    op.create_index("ix_official_player_match_stats_team_id", "official_player_match_stats", ["team_id"])
    op.create_index("ix_official_player_match_stats_player_id", "official_player_match_stats", ["player_id"])


def downgrade() -> None:
    op.drop_table("official_player_match_stats")
    op.drop_table("official_team_match_stats")
    op.drop_table("match_report_imports")

