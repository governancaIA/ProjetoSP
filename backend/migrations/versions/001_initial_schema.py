"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_email"),
    )
    op.create_index("ix_email", "users", ["email"])
    op.create_index("ix_tenant_email", "users", ["tenant_id", "email"])
    op.create_index(op.f("ix_users_id"), "users", ["id"])
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"])

    # --- refresh_tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_token_hash"),
    )
    op.create_index("ix_user_id", "refresh_tokens", ["user_id"])
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"])
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"])

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum("sped_efd_icms", "efd_contribuicoes", "nfe", "cte", "unknown", name="documenttype"),
            nullable=True,
        ),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("storage_bucket", sa.String(100), nullable=False),
        sa.Column("document_version", sa.Integer(), server_default="1"),
        sa.Column("superseded", sa.Boolean(), server_default="false"),
        sa.Column("processing_status", sa.String(50), server_default="pending"),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_id"), "documents", ["id"])
    op.create_index(op.f("ix_documents_tenant_id"), "documents", ["tenant_id"])
    op.create_index(op.f("ix_documents_file_hash"), "documents", ["file_hash"])
    op.create_index(op.f("ix_documents_celery_task_id"), "documents", ["celery_task_id"])
    op.create_index(op.f("ix_documents_created_at"), "documents", ["created_at"])

    # --- fiscal_documents ---
    op.create_table(
        "fiscal_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chave_acesso", sa.String(44), unique=True, nullable=True),
        sa.Column("numero_nf", sa.String(20), nullable=False),
        sa.Column("serie", sa.String(20), nullable=False),
        sa.Column("emitente_cnpj", sa.String(14), nullable=False),
        sa.Column("emitente_nome", sa.String(255), nullable=True),
        sa.Column("destinatario_cnpj", sa.String(14), nullable=True),
        sa.Column("destinatario_nome", sa.String(255), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("data_saida", sa.Date(), nullable=True),
        sa.Column("natureza", sa.String(50), nullable=True),
        sa.Column("valor_total", sa.Numeric(15, 2), nullable=False),
        sa.Column("valor_icms", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("valor_pis", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("valor_cofins", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("valor_ipi", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("status_nfe", sa.String(50), nullable=True),
        sa.Column("protocolo_nfe", sa.String(50), nullable=True),
        sa.Column("data_autorizacao", sa.DateTime(), nullable=True),
        sa.Column("chave_acesso_referenciada", sa.String(44), nullable=True),
        sa.Column("document_version", sa.Integer(), server_default="1"),
        sa.Column("superseded", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fiscal_documents_id"), "fiscal_documents", ["id"])
    op.create_index(op.f("ix_fiscal_documents_tenant_id"), "fiscal_documents", ["tenant_id"])
    op.create_index("ix_chave_acesso", "fiscal_documents", ["chave_acesso"])
    op.create_index("ix_tenant_chave", "fiscal_documents", ["tenant_id", "chave_acesso"])
    op.create_index("ix_emitente_data", "fiscal_documents", ["emitente_cnpj", "data_emissao"])
    op.create_index(op.f("ix_fiscal_documents_data_emissao"), "fiscal_documents", ["data_emissao"])

    # --- fiscal_items ---
    op.create_table(
        "fiscal_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("fiscal_document_id", sa.Integer(), nullable=False),
        sa.Column("item_seq", sa.Integer(), nullable=False),
        sa.Column("codigo_produto", sa.String(60), nullable=True),
        sa.Column("descricao", sa.String(255), nullable=True),
        sa.Column("ncm", sa.String(8), nullable=True),
        sa.Column("cfop", sa.String(4), nullable=False),
        sa.Column("cst", sa.String(2), nullable=False),
        sa.Column("quantidade", sa.Numeric(15, 4), nullable=False),
        sa.Column("unidade", sa.String(5), nullable=True),
        sa.Column("valor_unitario", sa.Numeric(15, 2), nullable=False),
        sa.Column("valor_item", sa.Numeric(15, 2), nullable=False),
        sa.Column("valor_desconto", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("base_icms", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("aliquota_icms", sa.Numeric(5, 2), server_default="0.00"),
        sa.Column("valor_icms", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("base_pis", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("aliquota_pis", sa.Numeric(5, 2), server_default="0.00"),
        sa.Column("valor_pis", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("base_cofins", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("aliquota_cofins", sa.Numeric(5, 2), server_default="0.00"),
        sa.Column("valor_cofins", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("valor_ipi", sa.Numeric(15, 2), server_default="0.00"),
        sa.Column("document_version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["fiscal_document_id"], ["fiscal_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fiscal_items_id"), "fiscal_items", ["id"])
    op.create_index(op.f("ix_fiscal_items_tenant_id"), "fiscal_items", ["tenant_id"])
    op.create_index("ix_fiscal_doc_seq", "fiscal_items", ["fiscal_document_id", "item_seq"])

    # --- ct_documents ---
    op.create_table(
        "ct_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chave_acesso", sa.String(44), unique=True, nullable=True),
        sa.Column("numero_cte", sa.String(20), nullable=False),
        sa.Column("serie", sa.String(20), nullable=False),
        sa.Column("transportador_cnpj", sa.String(14), nullable=False),
        sa.Column("transportador_nome", sa.String(255), nullable=True),
        sa.Column("remetente_cnpj", sa.String(14), nullable=True),
        sa.Column("destinatario_cnpj", sa.String(14), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("natureza_operacao", sa.String(50), nullable=True),
        sa.Column("valor_total", sa.Numeric(15, 2), nullable=False),
        sa.Column("status_cte", sa.String(50), nullable=True),
        sa.Column("protocolo_cte", sa.String(50), nullable=True),
        sa.Column("data_autorizacao", sa.DateTime(), nullable=True),
        sa.Column("document_version", sa.Integer(), server_default="1"),
        sa.Column("superseded", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ct_documents_id"), "ct_documents", ["id"])
    op.create_index(op.f("ix_ct_documents_tenant_id"), "ct_documents", ["tenant_id"])
    op.create_index("ix_chave_acesso_cte", "ct_documents", ["chave_acesso"])
    op.create_index("ix_tenant_chave_cte", "ct_documents", ["tenant_id", "chave_acesso"])

    # --- fiscal_rules_log ---
    op.create_table(
        "fiscal_rules_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("fiscal_document_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("rule_version", sa.String(20), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("CRITICAL", "WARNING", "INFO", name="severitylevel"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("input_snapshot", sa.JSON(), nullable=True),
        sa.Column("config_applied", sa.JSON(), nullable=True),
        sa.Column("triggered_by", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["fiscal_document_id"], ["fiscal_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fiscal_rules_log_id"), "fiscal_rules_log", ["id"])
    op.create_index(op.f("ix_fiscal_rules_log_tenant_id"), "fiscal_rules_log", ["tenant_id"])
    op.create_index(op.f("ix_fiscal_rules_log_rule_id"), "fiscal_rules_log", ["rule_id"])
    op.create_index("ix_doc_id", "fiscal_rules_log", ["fiscal_document_id"])
    op.create_index("ix_doc_rule", "fiscal_rules_log", ["fiscal_document_id", "rule_id"])
    op.create_index("ix_created", "fiscal_rules_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("fiscal_rules_log")
    op.drop_table("ct_documents")
    op.drop_table("fiscal_items")
    op.drop_table("fiscal_documents")
    op.drop_table("documents")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS severitylevel")
    op.execute("DROP TYPE IF EXISTS documenttype")
