"""add book ppt columns

Revision ID: df937d4d3ee7
Revises:
Create Date: 2026-03-30 21:22:16.666077

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "df937d4d3ee7"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "books",
        sa.Column("ppt_url", sa.String(), nullable=True),
    )
    op.add_column(
        "books",
        sa.Column(
            "ppt_status",
            sa.String(),
            nullable=False,
            server_default="not_generated",
        ),
    )


def downgrade():
    op.drop_column("books", "ppt_status")
    op.drop_column("books", "ppt_url")
