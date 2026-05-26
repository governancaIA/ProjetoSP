"""
Document service for fiscal document persistence
"""
from typing import Dict, List, Any, Union
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
import logging

from app.models.document import Document, DocumentType
from app.models.fiscal_document import FiscalDocument, FiscalItem
from app.models.ct_document import CTDocument
from app.core.database import set_tenant_schema
from app.parsers.sped_efd_icms import SPEDRecord

logger = logging.getLogger(__name__)


class DocumentServiceError(Exception):
    """Document service error"""
    pass


class DocumentService:
    """
    Service for persisting parsed documents to database.
    Handles fiscal documents (FiscalDocument + FiscalItem) and CT-e documents.
    """

    @staticmethod
    def create_document_record(
        db: Session,
        tenant_id: str,
        original_filename: str,
        document_type: DocumentType,
        file_hash: str,
        file_size: int,
        storage_key: str,
        storage_bucket: str,
    ) -> Document:
        """
        Create a Document record (parent for all parsed data).

        Args:
            db: SQLAlchemy session
            tenant_id: Organization/tenant ID
            original_filename: Original file name
            document_type: Type of document (sped_efd_icms, nfe, cte, etc)
            file_hash: SHA-256 hash
            file_size: File size in bytes
            storage_key: Storage key in MinIO
            storage_bucket: Storage bucket name

        Returns:
            Document instance (persisted)

        Raises:
            DocumentServiceError: If creation fails
        """
        try:
            # Check if document with same hash already exists (reprocessamento)
            existing = db.query(Document).filter_by(
                tenant_id=tenant_id,
                file_hash=file_hash,
            ).first()

            if existing:
                # Mark existing as superseded
                existing.superseded = True
                existing.document_version += 1
                document_version = existing.document_version
            else:
                document_version = 1

            doc = Document(
                tenant_id=tenant_id,
                original_filename=original_filename,
                document_type=document_type,
                file_hash=file_hash,
                file_size=file_size,
                storage_key=storage_key,
                storage_bucket=storage_bucket,
                document_version=document_version,
                processing_status="pending",
                superseded=False,
            )

            db.add(doc)
            db.flush()  # Get the ID without committing
            logger.info(f"Created Document record: id={doc.id}, hash={file_hash}")
            return doc

        except Exception as e:
            logger.error(f"Failed to create Document record: {str(e)}")
            raise DocumentServiceError(f"Failed to create Document: {str(e)}")

    @staticmethod
    def save_fiscal_document_from_sped(
        db: Session,
        tenant_id: str,
        document_id: int,
        parsed_sped: Dict[str, Any],
    ) -> List[FiscalDocument]:
        """
        Persist SPED parser output: C100 (headers) + C170 (items).

        Args:
            db: SQLAlchemy session
            tenant_id: Organization ID
            document_id: Parent Document ID
            parsed_sped: Output from SPEDParser.parse()

        Returns:
            List of persisted FiscalDocument instances

        Raises:
            DocumentServiceError: If save fails
        """
        try:
            fiscal_docs = []

            for c100 in parsed_sped.get("C100", []):
                # Create FiscalDocument from C100
                fiscal_doc = FiscalDocument(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    chave_acesso=c100.get("chave_acesso"),
                    numero_nf=c100.get("numero_nf"),
                    serie=c100.get("serie"),
                    emitente_cnpj=c100.get("emitente_cnpj", ""),
                    emitente_nome=c100.get("emitente_nome"),
                    destinatario_cnpj=c100.get("destinatario_cnpj"),
                    destinatario_nome=c100.get("destinatario_nome"),
                    data_emissao=DocumentService._parse_date(c100.get("data_emissao")),
                    data_saida=DocumentService._parse_date(c100.get("data_saida")),
                    natureza=c100.get("natureza"),
                    valor_total=Decimal(str(c100.get("valor_total", 0))),
                    valor_icms=Decimal(str(c100.get("valor_icms", 0))),
                    valor_pis=Decimal(str(c100.get("valor_pis", 0))),
                    valor_cofins=Decimal(str(c100.get("valor_cofins", 0))),
                    valor_ipi=Decimal(str(c100.get("valor_ipi", 0))),
                    status_nfe="cancelado" if c100.get("cancelado") else "autorizado",
                    document_version=1,
                )
                db.add(fiscal_doc)
                db.flush()

                # Add items (C170) — usa apenas os itens do C100 pai (hierarquia SPED)
                c170_list = c100.get("items", [])
                for item_idx, c170 in enumerate(c170_list, start=1):
                    item = FiscalItem(
                        tenant_id=tenant_id,
                        fiscal_document_id=fiscal_doc.id,
                        item_seq=item_idx,
                        codigo_produto=c170.get("codigo_item"),
                        descricao=c170.get("descricao"),
                        ncm=None,  # SPED C170 doesn't have NCM in this version
                        cfop=c170.get("cfop"),
                        cst=c170.get("cst"),
                        quantidade=Decimal(str(c170.get("quantidade", 0))),
                        unidade=c170.get("unidade"),
                        valor_unitario=Decimal(str(c170.get("valor_unitario", 0))),
                        valor_item=Decimal(str(c170.get("valor_item", 0))),
                        valor_desconto=Decimal(str(c170.get("valor_desc", 0))),
                        base_icms=Decimal(str(c170.get("valor_bc_icms", 0))),
                        aliquota_icms=Decimal(str(c170.get("aliq_icms", 0))),
                        valor_icms=Decimal(str(c170.get("valor_icms", 0))),
                        base_pis=Decimal(str(c170.get("valor_bc_pis", 0))),
                        aliquota_pis=Decimal(str(c170.get("aliq_pis", 0))),
                        valor_pis=Decimal(str(c170.get("valor_pis", 0))),
                        base_cofins=Decimal(str(c170.get("valor_bc_cofins", 0))),
                        aliquota_cofins=Decimal(str(c170.get("aliq_cofins", 0))),
                        valor_cofins=Decimal(str(c170.get("valor_cofins", 0))),
                        valor_ipi=Decimal(str(c170.get("valor_ipi", 0))),
                        document_version=1,
                    )
                    db.add(item)

                fiscal_docs.append(fiscal_doc)

            logger.info(f"Saved {len(fiscal_docs)} fiscal documents from SPED")
            return fiscal_docs

        except Exception as e:
            logger.error(f"Failed to save SPED fiscal documents: {str(e)}")
            raise DocumentServiceError(f"Failed to save SPED documents: {str(e)}")

    @staticmethod
    def save_fiscal_document_from_nfe(
        db: Session,
        tenant_id: str,
        document_id: int,
        parsed_nfe: Dict[str, Any],
    ) -> FiscalDocument:
        """
        Persist NF-e parser output.

        Args:
            db: SQLAlchemy session
            tenant_id: Organization ID
            document_id: Parent Document ID
            parsed_nfe: Output from NFEParser.parse()

        Returns:
            Persisted FiscalDocument instance

        Raises:
            DocumentServiceError: If save fails
        """
        try:
            nfe_data = parsed_nfe.get("nfe", {})

            fiscal_doc = FiscalDocument(
                tenant_id=tenant_id,
                document_id=document_id,
                chave_acesso=nfe_data.get("chave_acesso"),
                numero_nf=nfe_data.get("numero_nf"),
                serie=nfe_data.get("serie"),
                emitente_cnpj=nfe_data.get("emitente_cnpj", ""),
                emitente_nome=nfe_data.get("emitente_nome"),
                destinatario_cnpj=nfe_data.get("destinatario_cnpj"),
                destinatario_nome=nfe_data.get("destinatario_nome"),
                data_emissao=DocumentService._parse_date(nfe_data.get("data_emissao")),
                data_saida=DocumentService._parse_date(nfe_data.get("data_saida")),
                natureza=nfe_data.get("natureza"),
                valor_total=Decimal(str(nfe_data.get("valor_total", 0))),
                valor_icms=Decimal(str(nfe_data.get("valor_icms", 0))),
                valor_pis=Decimal(str(nfe_data.get("valor_pis", 0))),
                valor_cofins=Decimal(str(nfe_data.get("valor_cofins", 0))),
                valor_ipi=Decimal(str(nfe_data.get("valor_ipi", 0))),
                status_nfe=nfe_data.get("status"),
                protocolo_nfe=nfe_data.get("protocolo"),
                data_autorizacao=DocumentService._parse_datetime(nfe_data.get("data_autorizacao")),
                chave_acesso_referenciada=nfe_data.get("chave_acesso_referenciada"),
                document_version=1,
            )

            db.add(fiscal_doc)
            db.flush()

            # Add items
            for item_data in parsed_nfe.get("itens", []):
                item = FiscalItem(
                    tenant_id=tenant_id,
                    fiscal_document_id=fiscal_doc.id,
                    item_seq=item_data.get("item_seq", 0),
                    codigo_produto=item_data.get("codigo_produto"),
                    descricao=item_data.get("descricao"),
                    ncm=item_data.get("ncm"),
                    cfop=item_data.get("cfop"),
                    cst=item_data.get("cst", ""),
                    quantidade=Decimal(str(item_data.get("quantidade", 0))),
                    unidade=item_data.get("unidade"),
                    valor_unitario=Decimal(str(item_data.get("valor_unitario", 0))),
                    valor_item=Decimal(str(item_data.get("valor_item", 0))),
                    valor_desconto=Decimal(str(item_data.get("valor_desconto", 0))),
                    base_icms=Decimal(str(item_data.get("base_icms", 0))),
                    aliquota_icms=Decimal(str(item_data.get("aliquota_icms", 0))),
                    valor_icms=Decimal(str(item_data.get("valor_icms", 0))),
                    base_pis=Decimal(str(item_data.get("base_pis", 0))),
                    aliquota_pis=Decimal(str(item_data.get("aliquota_pis", 0))),
                    valor_pis=Decimal(str(item_data.get("valor_pis", 0))),
                    base_cofins=Decimal(str(item_data.get("base_cofins", 0))),
                    aliquota_cofins=Decimal(str(item_data.get("aliquota_cofins", 0))),
                    valor_cofins=Decimal(str(item_data.get("valor_cofins", 0))),
                    valor_ipi=Decimal(str(item_data.get("valor_ipi", 0))),
                    document_version=1,
                )
                db.add(item)

            logger.info(f"Saved NF-e fiscal document: {fiscal_doc.chave_acesso}")
            return fiscal_doc

        except Exception as e:
            logger.error(f"Failed to save NF-e fiscal document: {str(e)}")
            raise DocumentServiceError(f"Failed to save NF-e document: {str(e)}")

    @staticmethod
    def save_ct_document_from_cte(
        db: Session,
        tenant_id: str,
        document_id: int,
        parsed_cte: Dict[str, Any],
    ) -> CTDocument:
        """
        Persist CT-e parser output.

        Args:
            db: SQLAlchemy session
            tenant_id: Organization ID
            document_id: Parent Document ID
            parsed_cte: Output from CTEParser.parse()

        Returns:
            Persisted CTDocument instance

        Raises:
            DocumentServiceError: If save fails
        """
        try:
            cte_data = parsed_cte.get("cte", {})

            ct_doc = CTDocument(
                tenant_id=tenant_id,
                document_id=document_id,
                chave_acesso=cte_data.get("chave_acesso"),
                numero_cte=cte_data.get("numero_cte"),
                serie=cte_data.get("serie"),
                transportador_cnpj=cte_data.get("transportador_cnpj", ""),
                transportador_nome=cte_data.get("transportador_nome"),
                remetente_cnpj=cte_data.get("remetente_cnpj"),
                destinatario_cnpj=cte_data.get("destinatario_cnpj"),
                data_emissao=DocumentService._parse_date(cte_data.get("data_emissao")),
                natureza_operacao=cte_data.get("natureza_operacao"),
                valor_total=Decimal(str(cte_data.get("valor_total", 0))),
                status_cte=cte_data.get("status"),
                protocolo_cte=cte_data.get("protocolo"),
                data_autorizacao=DocumentService._parse_datetime(cte_data.get("data_autorizacao")),
                document_version=1,
            )

            db.add(ct_doc)
            logger.info(f"Saved CT-e document: {ct_doc.chave_acesso}")
            return ct_doc

        except Exception as e:
            logger.error(f"Failed to save CT-e document: {str(e)}")
            raise DocumentServiceError(f"Failed to save CT-e document: {str(e)}")

    @staticmethod
    def update_document_status(
        db: Session,
        document_id: int,
        status: str,
        error_message: str = None,
    ) -> None:
        """
        Update Document processing status.

        Args:
            db: SQLAlchemy session
            document_id: Document ID
            status: New status (pending, processing, completed, failed)
            error_message: Optional error message if status is failed

        Raises:
            DocumentServiceError: If update fails
        """
        try:
            doc = db.query(Document).filter_by(id=document_id).first()
            if not doc:
                raise DocumentServiceError(f"Document {document_id} not found")

            doc.processing_status = status
            if status == "completed":
                doc.processed_at = datetime.now(timezone.utc)
            if error_message:
                doc.processing_error = error_message

            logger.info(f"Updated Document {document_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update Document status: {str(e)}")
            raise DocumentServiceError(f"Failed to update status: {str(e)}")

    @staticmethod
    def _parse_date(date_str: str):
        """Parse date string (YYYY-MM-DD) to date object"""
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return None

    @staticmethod
    def _parse_datetime(datetime_str: str):
        """Parse ISO datetime string"""
        if not datetime_str:
            return None
        try:
            from dateutil import parser
            return parser.isoparse(datetime_str)
        except Exception:
            return None
