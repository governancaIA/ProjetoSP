"""
SPED EFD ICMS/IPI Parser

Parses pipe-delimited SPED files and extracts:
- 0000: file header (version, CNPJ, period, regime)
- C100: NF-e headers (with cancellation status from C110)
- C170: Item details with tax info
- D100: CT-e headers
- E110: ICMS apuração

Supports automatic encoding detection (Latin-1 / UTF-8) and
multi-version layout mapping via the 0000 record.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging

try:
    import chardet
    _CHARDET_AVAILABLE = True
except ImportError:
    _CHARDET_AVAILABLE = False

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when SPED parsing fails"""
    pass


# Known SPED EFD ICMS/IPI layout versions and their 0000 field positions.
# Based on Guia Prático EFD-ICMS/IPI (ENCAT/SEFAZ).
#
# From version 002 onwards (as observed in real files):
#   pos 0=cod_ver, 1=cod_fin, 2=dt_ini, 3=dt_fin, 4=nome, 5=cnpj, 6=cpf_or_empty,
#   7=uf, 8=cod_mun, 9=suframa, 10=ind_perfil, 11=ind_ativ
#
# Real file ARAMEFICIO (versão 012, jan/2018) confirms this layout:
#   |0000|012|0|01012018|31012018|NOME|66047275000199||SP|719006029118|3557204|||A|0|
#   fields after record type: [012, 0, dt_ini, dt_fin, nome, CNPJ, "", SP, ...]
_LAYOUT_STANDARD: Dict[str, int] = {
    "cod_ver": 0, "cod_fin": 1, "dt_ini": 2, "dt_fin": 3, "nome": 4,
    "cnpj": 5, "cpf": 6, "uf": 7, "cod_mun": 8, "suframa": 9,
    "ind_perfil": 10, "ind_ativ": 11,
}

_LAYOUT_VERSIONS: Dict[str, Dict[str, int]] = {
    v: _LAYOUT_STANDARD for v in (
        "002", "003", "004", "005", "006", "007", "008", "009",
        "010", "011", "012", "013", "014", "015", "016", "017",
    )
}
# Versions not in the map above use the standard layout as a fallback
_LATEST_LAYOUT = _LAYOUT_STANDARD

# C110 cancellation event code (Evento 110111 = cancelamento NF-e)
_CANCEL_COD = "110111"


def _detect_encoding(raw: bytes) -> str:
    """Detect file encoding, returning a Python codec name."""
    if _CHARDET_AVAILABLE:
        result = chardet.detect(raw[:65536])  # sample first 64 KB
        encoding = result.get("encoding") or "utf-8"
        confidence = result.get("confidence", 0)
        if confidence < 0.7:
            # Low confidence: SPED files pre-2015 are almost always Latin-1
            encoding = "latin-1"
        return encoding
    # Fallback: try UTF-8, then Latin-1
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def _get_layout(version: str) -> Dict[str, int]:
    """Return the field-position map for a given SPED version string."""
    # Normalize: "017" == "17" == "Versão 17"
    v = version.strip().lstrip("0") or "0"
    # Pad to 3 digits for lookup
    v_padded = v.zfill(3)
    if v_padded in _LAYOUT_VERSIONS:
        return _LAYOUT_VERSIONS[v_padded]
    # If version >= 17, use latest; otherwise use oldest known
    try:
        if int(v) >= 17:
            return _LATEST_LAYOUT
        return _LAYOUT_VERSIONS["016"]
    except ValueError:
        return _LATEST_LAYOUT


class SPEDRecord:
    """Utility methods for pipe-delimited record parsing."""

    @staticmethod
    def parse_field(fields: List[str], index: int, default: str = "") -> str:
        if index < len(fields):
            return fields[index]
        return default

    @staticmethod
    def parse_decimal(value: str, default: float = 0.0) -> float:
        if not value:
            return default
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return default


class Record0000(SPEDRecord):
    """SPED file header — record 0000."""

    @staticmethod
    def parse(fields: List[str], layout: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        if layout is None:
            # Without a known version, use raw positional extraction
            layout = _LATEST_LAYOUT

        def _f(key: str) -> str:
            idx = layout.get(key, -1)
            return Record0000.parse_field(fields, idx) if idx >= 0 else ""

        return {
            "record_type": "0000",
            "cod_ver": _f("cod_ver"),
            "cod_fin": _f("cod_fin"),
            "dt_ini": _f("dt_ini"),
            "dt_fin": _f("dt_fin"),
            "nome": _f("nome"),
            "cnpj": _f("cnpj"),
            "uf": _f("uf"),
            "cod_mun": _f("cod_mun"),
            "ind_perfil": _f("ind_perfil"),
            "ind_ativ": _f("ind_ativ"),
        }


class C100Record(SPEDRecord):
    """NF-e Header Record (C100)."""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        ind_emitente = C100Record.parse_field(fields, 1)
        natureza = "saida" if ind_emitente == "0" else "entrada"

        return {
            "record_type": "C100",
            "ind_mov": C100Record.parse_field(fields, 0),
            "ind_emitente": ind_emitente,
            "natureza": natureza,
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
            "cancelado": False,   # updated when a child C110 with cod_inf=110111 is found
        }


class C170Record(SPEDRecord):
    """NF-e Item Detail Record (C170)."""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
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
    """CT-e Header Record (D100)."""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
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
    """ICMS Apuração Record (E110)."""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
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
    """Main SPED EFD ICMS/IPI parser."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.warnings: List[str] = []

    def parse_bytes(self, raw: bytes) -> Dict[str, Any]:
        """
        Parse raw bytes, auto-detecting encoding before decode.

        Prefer this over parse() when you have bytes (file upload, MinIO read).
        """
        encoding = _detect_encoding(raw)
        try:
            content = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            content = raw.decode("latin-1", errors="replace")
            self.warnings.append(f"Encoding fallback to latin-1 (detected: {encoding})")
        return self.parse(content)

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse SPED content string line-by-line.

        Returns:
            {
                "0000": {...},       # file header metadata
                "C100": [...],       # NF headers (cancelado=True when C110 found)
                "C170": [...],       # items
                "D100": [...],       # CT-e headers
                "E110": [...],       # ICMS apuração
                "metadata": {...}
            }
        """
        if not content or not content.strip():
            raise ParseError("SPED content is empty")

        self.warnings = []
        result: Dict[str, Any] = {
            "0000": {},
            "C100": [],
            "C170": [],
            "D100": [],
            "E110": [],
            "metadata": {},
        }

        lines = content.split("\n")
        current_c100: Optional[Dict[str, Any]] = None
        file_version: str = ""
        layout: Dict[str, int] = _LATEST_LAYOUT
        line_num = 0

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            fields = line.split("|")

            # Handle both |RECORD|... and RECORD|... formats
            if fields[0] == "" and len(fields) > 1:
                record_type = fields[1]
                offset = 1
            elif fields[0] != "":
                record_type = fields[0]
                offset = 0
            else:
                self.warnings.append(f"Line {line_num}: invalid format")
                continue

            # Data fields start after the record type field
            data_fields = fields[offset + 1:]

            try:
                if record_type == "0000":
                    # First pass: extract version to select layout
                    raw_ver = data_fields[0] if data_fields else ""
                    layout = _get_layout(raw_ver)
                    file_version = raw_ver
                    result["0000"] = Record0000.parse(data_fields, layout)
                    if raw_ver and raw_ver not in _LAYOUT_VERSIONS:
                        self.warnings.append(
                            f"Versão SPED desconhecida '{raw_ver}' — usando layout mais recente"
                        )

                elif record_type == "C100":
                    record = C100Record.parse(data_fields)
                    record["items"] = []
                    result["C100"].append(record)
                    current_c100 = record

                elif record_type == "C110":
                    # C110: NF-e complementary info — may carry cancellation event
                    cod_inf = data_fields[0] if data_fields else ""
                    if cod_inf == _CANCEL_COD and current_c100 is not None:
                        current_c100["cancelado"] = True

                elif record_type == "C170":
                    record = C170Record.parse(data_fields)
                    result["C170"].append(record)
                    if current_c100 is not None:
                        current_c100["items"].append(record)

                elif record_type == "D100":
                    record = D100Record.parse(data_fields)
                    result["D100"].append(record)
                    current_c100 = None  # D100 ends block C

                elif record_type == "E110":
                    result["E110"].append(E110Record.parse(data_fields))

                elif record_type in ("9", "0"):
                    pass  # trailer / block headers

            except Exception as exc:
                self.warnings.append(f"Line {line_num}: failed to parse {record_type}: {exc}")
                logger.warning("Line %d: failed to parse %s: %s", line_num, record_type, exc)

        # Post-process: propagate cancellation to status_nfe field for document_service
        for c100 in result["C100"]:
            if c100.get("cancelado"):
                c100["status_nfe"] = "cancelado"
            else:
                c100.setdefault("status_nfe", "autorizado")

        result["metadata"] = {
            "tenant_id": self.tenant_id,
            "file_version": file_version,
            "layout_used": "017" if layout is _LATEST_LAYOUT else file_version.zfill(3),
            "total_c100_records": len(result["C100"]),
            "total_c170_records": len(result["C170"]),
            "total_d100_records": len(result["D100"]),
            "total_e110_records": len(result["E110"]),
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "warnings": self.warnings,
            "total_lines_processed": line_num,
        }

        return result
