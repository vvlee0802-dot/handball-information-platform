"""add user roles and permissions

Revision ID: e4f7a2c9b610
Revises: c8e91a4f2d70
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f7a2c9b610"
down_revision: Union[str, Sequence[str], None] = "c8e91a4f2d70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(30), nullable=True),
    )
    op.execute("UPDATE users SET role = 'system_admin' WHERE role IS NULL")
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(30),
        nullable=False,
        server_default="athlete",
    )

    op.create_table(
        "user_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "permission",
            name="uq_user_permissions_user_permission",
        ),
    )
    op.create_index(
        "ix_user_permissions_user_id",
        "user_permissions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("user_permissions")
    op.drop_column("users", "role")
