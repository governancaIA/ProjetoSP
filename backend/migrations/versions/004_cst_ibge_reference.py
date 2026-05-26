"""add cst_icms_reference and ibge_uf tables

Revision ID: 004
Revises: 003
Create Date: 2026-05-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# fmt: off
# CST ICMS codes per Anexo I do Convênio S/N de 15/12/1970 (Tabela A) and
# Tabela B introduced by LC 123/2006 (Simples Nacional).
# Fields: (cst, descricao, tabela, regime_lucro_real, regime_lucro_presumido, regime_simples)
_CST_ICMS = [
    # ── Tabela A — regime normal (Lucro Real e Lucro Presumido) ─────────────
    ("00", "Tributada integralmente",                                                            "A", True,  True,  False),
    ("10", "Tributada e com cobrança do ICMS por substituição tributária",                       "A", True,  True,  False),
    ("20", "Com redução de base de cálculo",                                                     "A", True,  True,  False),
    ("30", "Isenta ou não tributada e com cobrança do ICMS por substituição tributária",         "A", True,  True,  False),
    ("40", "Isenta",                                                                             "A", True,  True,  False),
    ("41", "Não tributada",                                                                      "A", True,  True,  False),
    ("50", "Suspensão",                                                                          "A", True,  True,  False),
    ("51", "Diferimento",                                                                        "A", True,  True,  False),
    ("60", "ICMS cobrado anteriormente por substituição tributária",                             "A", True,  True,  False),
    ("70", "Com redução de base de cálculo e cobrança do ICMS por substituição tributária",      "A", True,  True,  False),
    ("90", "Outras",                                                                             "A", True,  True,  False),
    # ── Tabela B — Simples Nacional ──────────────────────────────────────────
    ("101", "Tributada pelo Simples Nacional com permissão de crédito",                         "B", False, False, True),
    ("102", "Tributada pelo Simples Nacional sem permissão de crédito",                         "B", False, False, True),
    ("103", "Isenção do ICMS no Simples Nacional para faixa de receita bruta",                  "B", False, False, True),
    ("201", "Tributada pelo Simples Nacional com permissão de crédito e com cobrança do ICMS por ST", "B", False, False, True),
    ("202", "Tributada pelo Simples Nacional sem permissão de crédito e com cobrança do ICMS por ST", "B", False, False, True),
    ("203", "Isenção do ICMS no Simples Nacional para faixa de receita bruta e com cobrança do ICMS por ST", "B", False, False, True),
    ("300", "Imune",                                                                             "B", False, False, True),
    ("400", "Não tributada pelo Simples Nacional",                                               "B", False, False, True),
    ("500", "ICMS cobrado anteriormente por ST ou por antecipação",                              "B", False, False, True),
    ("900", "Outras (Simples Nacional)",                                                         "B", False, False, True),
]

# IBGE UF codes — Resolução IBGE n° 5 de 10/10/2002 (updated 2018)
# Fields: (codigo_ibge, uf, nome, regiao)
_UFS = [
    (11, "RO", "Rondônia",             "N"),
    (12, "AC", "Acre",                 "N"),
    (13, "AM", "Amazonas",             "N"),
    (14, "RR", "Roraima",              "N"),
    (15, "PA", "Pará",                 "N"),
    (16, "AP", "Amapá",                "N"),
    (17, "TO", "Tocantins",            "N"),
    (21, "MA", "Maranhão",             "NE"),
    (22, "PI", "Piauí",                "NE"),
    (23, "CE", "Ceará",                "NE"),
    (24, "RN", "Rio Grande do Norte",  "NE"),
    (25, "PB", "Paraíba",              "NE"),
    (26, "PE", "Pernambuco",           "NE"),
    (27, "AL", "Alagoas",              "NE"),
    (28, "SE", "Sergipe",              "NE"),
    (29, "BA", "Bahia",                "NE"),
    (31, "MG", "Minas Gerais",         "SE"),
    (32, "ES", "Espírito Santo",       "SE"),
    (33, "RJ", "Rio de Janeiro",       "SE"),
    (35, "SP", "São Paulo",            "SE"),
    (41, "PR", "Paraná",               "S"),
    (42, "SC", "Santa Catarina",       "S"),
    (43, "RS", "Rio Grande do Sul",    "S"),
    (50, "MS", "Mato Grosso do Sul",   "CO"),
    (51, "MT", "Mato Grosso",          "CO"),
    (52, "GO", "Goiás",                "CO"),
    (53, "DF", "Distrito Federal",     "CO"),
]
# fmt: on


def upgrade() -> None:
    # ── cst_icms_reference ───────────────────────────────────────────────────
    op.create_table(
        "cst_icms_reference",
        sa.Column("cst", sa.String(3), primary_key=True),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("tabela", sa.String(1), nullable=False),
        sa.Column("regime_lucro_real", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("regime_lucro_presumido", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("regime_simples", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_cst_tabela", "cst_icms_reference", ["tabela"])

    op.bulk_insert(
        sa.table(
            "cst_icms_reference",
            sa.column("cst", sa.String),
            sa.column("descricao", sa.String),
            sa.column("tabela", sa.String),
            sa.column("regime_lucro_real", sa.Boolean),
            sa.column("regime_lucro_presumido", sa.Boolean),
            sa.column("regime_simples", sa.Boolean),
            sa.column("ativo", sa.Boolean),
        ),
        [
            {
                "cst": r[0],
                "descricao": r[1],
                "tabela": r[2],
                "regime_lucro_real": r[3],
                "regime_lucro_presumido": r[4],
                "regime_simples": r[5],
                "ativo": True,
            }
            for r in _CST_ICMS
        ],
    )

    # ── ibge_uf ──────────────────────────────────────────────────────────────
    op.create_table(
        "ibge_uf",
        sa.Column("codigo_ibge", sa.Integer(), primary_key=True),
        sa.Column("uf", sa.String(2), nullable=False, unique=True),
        sa.Column("nome", sa.String(50), nullable=False),
        sa.Column("regiao", sa.String(2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_ibge_uf_uf", "ibge_uf", ["uf"])

    op.bulk_insert(
        sa.table(
            "ibge_uf",
            sa.column("codigo_ibge", sa.Integer),
            sa.column("uf", sa.String),
            sa.column("nome", sa.String),
            sa.column("regiao", sa.String),
            sa.column("ativo", sa.Boolean),
        ),
        [
            {"codigo_ibge": r[0], "uf": r[1], "nome": r[2], "regiao": r[3], "ativo": True}
            for r in _UFS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_ibge_uf_uf", table_name="ibge_uf")
    op.drop_table("ibge_uf")
    op.drop_index("ix_cst_tabela", table_name="cst_icms_reference")
    op.drop_table("cst_icms_reference")
