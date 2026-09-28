"""add knowledge embeddings

Revision ID: b2f7c9d4e810
Revises: a9d4e7c1b260
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2f7c9d4e810"
down_revision: Union[str, Sequence[str], None] = "a9d4e7c1b260"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("embedding", sa.JSON(), nullable=True))
    op.add_column("document_chunks", sa.Column("embedding_model", sa.String(length=120), nullable=True))
    op.add_column("document_chunks", sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "embedded_at")
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "embedding")
