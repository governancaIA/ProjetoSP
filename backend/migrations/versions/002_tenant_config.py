"""add tenant_configs table

Revision ID: 002
Revises: 001
Create Date: 2026-05-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, unique=True),
        sa.Column("cnpj_principal", sa.String(14), nullable=True),
        sa.Column("razao_social", sa.String(255), nullable=True),
        sa.Column("uf", sa.String(2), nullable=True),
        sa.Column("regime_tributario", sa.String(50), nullable=True),
        sa.Column("tolerance_brl", sa.Numeric(10, 2), nullable=True),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_tenant_config_tenant_id", "tenant_configs", ["tenant_id"])
    op.create_index("ix_tenant_config_tenant_id", "tenant_configs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_config_tenant_id", table_name="tenant_configs")
    op.drop_constraint("uq_tenant_config_tenant_id", "tenant_configs", type_="unique")
    op.drop_table("tenant_configs")
