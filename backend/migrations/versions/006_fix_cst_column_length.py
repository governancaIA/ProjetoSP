"""fix fiscal_items.cst column length from 2 to 3 (Simples Nacional CSTs)

Revision ID: 006
Revises: 005
Create Date: 2026-05-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "fiscal_items",
        "cst",
        existing_type=sa.String(2),
        type_=sa.String(3),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "fiscal_items",
        "cst",
        existing_type=sa.String(3),
        type_=sa.String(2),
        existing_nullable=False,
    )
