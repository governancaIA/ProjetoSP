"""
SPED EFD ICMS/IPI Parser (US-1.4)

Parses pipe-delimited SPED files line-by-line and extracts:
- C100: NF headers
- C170: Item details with tax info
- D100: CT-e headers
- E110: ICMS apuracao
"""
from typing import Dict, List, Any
from datetime import datetime, timezone
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when SPED parsing fails"""
    pass


class CST(str, Enum):
    """CST (Código de Situação Tributária) codes for ICMS"""
    # Tributado
    CST_00 = "00"  # Tributada integralmente
    CST_10 = "10"  # Tributada com suspensão
    CST_20 = "20"  # Com redução de base
    CST_30 = "30"  # Isenta
    CST_40 = "40"  # Não tributada
    CST_41 = "41"  # Não tributada (exportação)
    CST_50 = "50"  # Suspensão
    CST_60 = "60"  # ICMS cobrado anteriormente
    CST_70 = "70"  # Com redução e cobrança do ICMS
    CST_90 = "90"  # Outras


class SPEDRecord:
    """Base class for SPED record parsing"""

    @staticmethod
    def parse_field(fields: List[str], index: int, default: str = "") -> str:
        """Safely extract field from pipe-delimited line"""
        if index < len(fields):
            return fields[index]
        return default

    @staticmethod
    def parse_decimal(value: str, default: float = 0.0) -> float:
        """Parse decimal value safely (handles comma as decimal separator)"""
        if not value:
            return default
        try:
            # SPED uses comma as decimal separator
            normalized = value.replace(',', '.')
            return float(normalized)
        except ValueError:
            return default


class C100Record(SPEDRecord):
    """NF-e Header Record (C100)"""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        """
        Parse C100 record: [ind_mov,ind_emitente,serie,modelo,numero_nf,...]

        Fields (0-indexed, after removing record type):
        0: ind_mov
        1: ind_emitente
        2: serie (numeric)
        3: modelo (55=NFe, 01=CTe)
        4: serie_nf_ecf (alpha)
        5: ???
        6: numero_nf
        7: chave_acesso
        8: data_emissao
        9: data_saida_entrada
        10: valor_total
        ... and more
        """
        return {
            "record_type": "C100",
            "ind_mov": C100Record.parse_field(fields, 0),
            "ind_emitente": C100Record.parse_field(fields, 1),
            "serie": C100Record.parse_field(fields, 2),
            "modelo": C100Record.parse_field(fields, 3),
            "serie_nf_ecf": C100Record.parse_field(fields, 4),
            "unknown_field_5": C100Record.parse_field(fields, 5),
            "numero_nf": C100Record.parse_field(fields, 6),
            "chave_acesso": C100Record.parse_field(fields, 7),
            "data_emissao": C100Record.parse_field(fields, 8),
            "data_saida_entrada": C100Record.parse_field(fields, 9),
            "valor_total": C100Record.parse_field(fields, 10),
            "ind_pagto": C100Record.parse_field(fields, 11),
            "valor_desc": C100Record.parse_field(fields, 12),
            "valor_abatimento": C100Record.parse_field(fields, 13),
            "valor_merc": C100Record.parse_field(fields, 14),
            "ind_st": C100Record.parse_field(fields, 15),
            "valor_st": C100Record.parse_field(fields, 16),
            "valor_frete": C100Record.parse_field(fields, 17),
            "valor_seguro": C100Record.parse_field(fields, 18),
            "valor_outr": C100Record.parse_field(fields, 19),
            "valor_ipi": C100Record.parse_field(fields, 20),
            "valor_pis": C100Record.parse_field(fields, 21),
            "valor_cofins": C100Record.parse_field(fields, 22),
        }


class C170Record(SPEDRecord):
    """NF-e Item Detail Record (C170)"""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        """
        Parse C170 record: [numero_seq,codigo_item,descricao,...]

        Fields (0-indexed):
        0: numero_sequencial
        1: codigo_item
        2: descricao
        3: (empty/unused)
        4: quantidade
        5: unidade
        6: valor_unitario
        7: valor_desc
        8: ind_mov
        9: cfop
        10: cst
        11: valor_icms
        ... etc
        """
        return {
            "record_type": "C170",
            "numero_sequencial": C170Record.parse_field(fields, 0),
            "codigo_item": C170Record.parse_field(fields, 1),
            "descricao": C170Record.parse_field(fields, 2),
            "quantidade": C170Record.parse_field(fields, 3),
            "unidade": C170Record.parse_field(fields, 4),
            "valor_unitario": C170Record.parse_field(fields, 5),
            "valor_desc": C170Record.parse_field(fields, 6),
            "ind_mov": C170Record.parse_field(fields, 7),
            "cfop": C170Record.parse_field(fields, 8),
            "cst": C170Record.parse_field(fields, 9),
            "valor_icms": C170Record.parse_field(fields, 10),
            "aliq_icms": C170Record.parse_field(fields, 11),
            "valor_bc_icms": C170Record.parse_field(fields, 12),
            "valor_ipi": C170Record.parse_field(fields, 13),
            "aliq_ipi": C170Record.parse_field(fields, 14),
            "valor_pis": C170Record.parse_field(fields, 15),
            "aliq_pis": C170Record.parse_field(fields, 16),
            "valor_cofins": C170Record.parse_field(fields, 17),
            "aliq_cofins": C170Record.parse_field(fields, 18),
        }


class D100Record(SPEDRecord):
    """CT-e Header Record (D100)"""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        """Parse D100 record: [ind_emitente,ind_cte,serie,numero_cte,...]"""
        return {
            "record_type": "D100",
            "ind_emitente": D100Record.parse_field(fields, 0),
            "ind_cte": D100Record.parse_field(fields, 1),
            "serie": D100Record.parse_field(fields, 2),
            "numero_cte": D100Record.parse_field(fields, 3),
            "chave_acesso": D100Record.parse_field(fields, 4),
            "data_emissao": D100Record.parse_field(fields, 5),
            "data_saida_coleta": D100Record.parse_field(fields, 6),
            "valor_total": D100Record.parse_field(fields, 7),
            "valor_icms": D100Record.parse_field(fields, 8),
        }


class E110Record(SPEDRecord):
    """ICMS Apuração Record (E110)"""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        """Parse E110 record: [valor_total_bc,aliq_icms,valor_icms,...]"""
        return {
            "record_type": "E110",
            "valor_total_bc": E110Record.parse_field(fields, 0),
            "aliq_icms": E110Record.parse_field(fields, 1),
            "valor_icms": E110Record.parse_field(fields, 2),
            "valor_outr": E110Record.parse_field(fields, 3),
            "valor_deducoes": E110Record.parse_field(fields, 4),
            "valor_ajustes": E110Record.parse_field(fields, 5),
        }


class SPEDParser:
    """Main SPED EFD ICMS/IPI parser"""

    def __init__(self, tenant_id: str):
        """Initialize parser for a specific tenant"""
        self.tenant_id = tenant_id
        self.warnings: List[str] = []

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse SPED content line-by-line

        Args:
            content: Full SPED file content as string

        Returns:
            {
                "C100": [...],  # NF headers
                "C170": [...],  # Items with tax info
                "D100": [...],  # CT-e headers
                "E110": [...],  # ICMS apuracao
                "metadata": {...}
            }

        Raises:
            ParseError: If content is empty or invalid
        """
        if not content or not content.strip():
            raise ParseError("SPED content is empty")

        self.warnings = []
        result = {
            "C100": [],
            "C170": [],
            "D100": [],
            "E110": [],
            "metadata": {},
        }

        lines = content.split('\n')
        current_c100_idx = None

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            fields = line.split('|')

            # Handle both formats: |RECORD| and RECORD|
            # If line starts with |, fields[0] is empty and record_type is fields[1]
            # Otherwise, record_type is fields[0]
            if fields[0] == "" and len(fields) > 1:
                record_type = fields[1]
                offset = 1
            elif fields[0] != "":
                record_type = fields[0]
                offset = 0
            else:
                self.warnings.append(f"Line {line_num}: Invalid format")
                continue

            try:
                # Extract actual data fields (skip record type)
                if offset > 0:
                    # Line starts with |record_type|, so skip fields[0] and fields[1]
                    data_fields = fields[offset + 1:]
                else:
                    # Line starts with record_type|, so skip just the record type
                    data_fields = fields[1:]

                if record_type == "C100":
                    record = C100Record.parse(data_fields)
                    result["C100"].append(record)
                    current_c100_idx = len(result["C100"]) - 1

                elif record_type == "C170":
                    record = C170Record.parse(data_fields)
                    result["C170"].append(record)

                elif record_type == "D100":
                    record = D100Record.parse(data_fields)
                    result["D100"].append(record)

                elif record_type == "E110":
                    record = E110Record.parse(data_fields)
                    result["E110"].append(record)

                elif record_type in ["9", "0"]:
                    # Trailer (9) and header (0) - skip
                    pass

            except Exception as e:
                self.warnings.append(f"Line {line_num}: Failed to parse {record_type}: {str(e)}")
                logger.warning(f"Line {line_num}: Failed to parse {record_type}: {str(e)}")

        result["metadata"] = {
            "tenant_id": self.tenant_id,
            "total_c100_records": len(result["C100"]),
            "total_c170_records": len(result["C170"]),
            "total_d100_records": len(result["D100"]),
            "total_e110_records": len(result["E110"]),
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "warnings": self.warnings,
            "total_lines_processed": line_num if 'line_num' in locals() else 0,
        }

        return result
