"""add team scoped knowledge

Revision ID: c5e8a1d7f940
Revises: b2f7c9d4e810
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c5e8a1d7f940"
down_revision: Union[str, Sequence[str], None] = "b2f7c9d4e810"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("team_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_team_id_teams",
        "users",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_team_id", "users", ["team_id"])
    op.add_column("knowledge_documents", sa.Column("team_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_knowledge_documents_team_id_teams",
        "knowledge_documents",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_knowledge_documents_team_id", "knowledge_documents", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_documents_team_id", table_name="knowledge_documents")
    op.drop_constraint(
        "fk_knowledge_documents_team_id_teams",
        "knowledge_documents",
        type_="foreignkey",
    )
    op.drop_column("knowledge_documents", "team_id")
    op.drop_index("ix_users_team_id", table_name="users")
    op.drop_constraint("fk_users_team_id_teams", "users", type_="foreignkey")
    op.drop_column("users", "team_id")
