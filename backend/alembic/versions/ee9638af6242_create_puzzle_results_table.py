"""create puzzle_results table

Revision ID: ee9638af6242
Revises: 
Create Date: 2026-06-24 13:04:29.928209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee9638af6242'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "puzzle_results",
        sa.Column("puzzle_number", sa.Integer(), nullable=False),
        sa.Column("extract_id", sa.String(), nullable=False),
        sa.Column("board_width", sa.Integer(), nullable=False),
        sa.Column("board_height", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("patches_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("upload_filename", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("puzzle_number"),
        sa.UniqueConstraint("extract_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("puzzle_results")
