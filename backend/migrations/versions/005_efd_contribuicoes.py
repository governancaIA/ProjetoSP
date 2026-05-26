"""add efd_contribuicoes and efd_contribuicoes_cst tables

Revision ID: 005
Revises: 004
Create Date: 2026-05-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "efd_contribuicoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("dt_ini", sa.Date(), nullable=False),
        sa.Column("dt_fin", sa.Date(), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("nome", sa.String(255), nullable=True),
        sa.Column("uf", sa.String(2), nullable=True),
        sa.Column("ind_reg_cum", sa.String(1), nullable=True),
        sa.Column("cod_tipo_contrib", sa.String(1), nullable=True),
        sa.Column("pis_vl_contrib", sa.Numeric(15, 2), nullable=True, server_default="0.00"),
        sa.Column("pis_vl_cred_desc", sa.Numeric(15, 2), nullable=True, server_default="0.00"),
        sa.Column("pis_vl_saldo_devedor", sa.Numeric(15, 2), nullable=True, server_default="0.00"),
        sa.Column("cofins_vl_contrib", sa.Numeric(15, 2), nullable=True, server_default="0.00"),
        sa.Column("cofins_vl_cred_desc", sa.Numeric(15, 2), nullable=True, server_default="0.00"),
        sa.Column("cofins_vl_saldo_devedor", sa.Numeric(15, 2), nullable=True, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_efd_contrib_tenant_periodo", "efd_contribuicoes", ["tenant_id", "dt_ini"])

    op.create_table(
        "efd_contribuicoes_cst",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, index=True),
        sa.Column("efd_contribuicoes_id", sa.Integer(),
                  sa.ForeignKey("efd_contribuicoes.id"), nullable=False),
        sa.Column("tipo", sa.String(6), nullable=False),
        sa.Column("cst", sa.String(2), nullable=False),
        sa.Column("vl_bc", sa.Numeric(15, 2), nullable=True, server_default="0.00"),
        sa.Column("aliq_perc", sa.Numeric(8, 4), nullable=True, server_default="0.0000"),
        sa.Column("vl_cred", sa.Numeric(15, 2), nullable=True, server_default="0.00"),
    )
    op.create_index("ix_efd_cst_efd_id", "efd_contribuicoes_cst", ["efd_contribuicoes_id"])
    op.create_index("ix_efd_cst_tipo_cst", "efd_contribuicoes_cst", ["tipo", "cst"])


def downgrade() -> None:
    op.drop_index("ix_efd_cst_tipo_cst", table_name="efd_contribuicoes_cst")
    op.drop_index("ix_efd_cst_efd_id", table_name="efd_contribuicoes_cst")
    op.drop_table("efd_contribuicoes_cst")
    op.drop_index("ix_efd_contrib_tenant_periodo", table_name="efd_contribuicoes")
    op.drop_table("efd_contribuicoes")
