"""verify manual events

Revision ID: d9a2f7c4e681
Revises: c6d8f1a3b520
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d9a2f7c4e681"
down_revision: Union[str, Sequence[str], None] = "c6d8f1a3b520"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE events
        SET status = 'verified',
            verified_at = COALESCE(verified_at, updated_at, created_at, now()),
            verified_by_user_id = COALESCE(
                verified_by_user_id,
                updated_by_user_id,
                created_by_user_id
            )
        WHERE source = 'manual' AND status = 'draft'
        """
    )


def downgrade() -> None:
    # Verification is user data. Downgrading must not silently turn confirmed events
    # back into drafts because migrations cannot distinguish old rows from new ones.
    pass
