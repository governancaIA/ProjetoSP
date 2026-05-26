"""
EFD Contribuições Parser (PIS/COFINS)

Extracts PIS and COFINS apuração records:
- 0000: file header
- M100: PIS credit per CST
- M200: PIS total apuração
- M400: COFINS credit per CST
- M500: COFINS total apuração

Supports automatic encoding detection (Latin-1 / UTF-8) via chardet.
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


class EFDContribuicoesParseError(Exception):
    pass


def _detect_encoding(raw: bytes) -> str:
    if _CHARDET_AVAILABLE:
        result = chardet.detect(raw[:65536])
        encoding = result.get("encoding") or "utf-8"
        if (result.get("confidence") or 0) < 0.7:
            encoding = "latin-1"
        return encoding
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


class EFDContribRecord:
    @staticmethod
    def _f(fields: List[str], idx: int, default: str = "") -> str:
        return fields[idx] if idx < len(fields) else default

    @staticmethod
    def _dec(value: str, default: float = 0.0) -> float:
        if not value:
            return default
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return default


class M100Record(EFDContribRecord):
    """PIS/PASEP — crédito por CST (M100)."""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        return {
            "record_type": "M100",
            "cst_pis": M100Record._f(fields, 0),
            "vl_bc_pis": M100Record._dec(M100Record._f(fields, 1)),
            "aliq_pis_perc": M100Record._dec(M100Record._f(fields, 2)),
            "quant_bc_pis": M100Record._dec(M100Record._f(fields, 3)),
            "aliq_pis_real": M100Record._dec(M100Record._f(fields, 4)),
            "vl_cred": M100Record._dec(M100Record._f(fields, 5)),
            "vl_bc_pis_ain": M100Record._dec(M100Record._f(fields, 6)),
            "aliq_pis_ain": M100Record._dec(M100Record._f(fields, 7)),
            "vl_cred_ain": M100Record._dec(M100Record._f(fields, 8)),
            "vl_cred_desc": M100Record._dec(M100Record._f(fields, 9)),
            "vl_cred_desc_ain": M100Record._dec(M100Record._f(fields, 10)),
            "vl_cred_desc_pa_ant": M100Record._dec(M100Record._f(fields, 11)),
            "vl_cred_dispo": M100Record._dec(M100Record._f(fields, 12)),
            "vl_cred_isento": M100Record._dec(M100Record._f(fields, 13)),
            "vl_cred_desc_cumul": M100Record._dec(M100Record._f(fields, 14)),
        }


class M200Record(EFDContribRecord):
    """PIS/PASEP — total de contribuição apurada (M200)."""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        return {
            "record_type": "M200",
            "vl_tot_cont_nc_per": M200Record._dec(M200Record._f(fields, 0)),
            "vl_tot_cred_desc": M200Record._dec(M200Record._f(fields, 1)),
            "vl_tot_cred_desc_ain": M200Record._dec(M200Record._f(fields, 2)),
            "vl_tot_cred_desc_pa_ant": M200Record._dec(M200Record._f(fields, 3)),
            "vl_tot_cont_nc_dev": M200Record._dec(M200Record._f(fields, 4)),
            "vl_ret": M200Record._dec(M200Record._f(fields, 5)),
            "vl_out_ded": M200Record._dec(M200Record._f(fields, 6)),
            "vl_cont_dev_per": M200Record._dec(M200Record._f(fields, 7)),
            "vl_cont_ref_ant": M200Record._dec(M200Record._f(fields, 8)),
            "vl_tot_cont_cum": M200Record._dec(M200Record._f(fields, 9)),
            "vl_ret_nc": M200Record._dec(M200Record._f(fields, 10)),
            "vl_out_ded_nc": M200Record._dec(M200Record._f(fields, 11)),
            "vl_cont_dev_per_nc": M200Record._dec(M200Record._f(fields, 12)),
            "vl_cont_ref_ant_nc": M200Record._dec(M200Record._f(fields, 13)),
        }


class M400Record(EFDContribRecord):
    """COFINS — crédito por CST (M400)."""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        # M400 has the same structure as M100 (same field layout, different tax)
        return {
            "record_type": "M400",
            "cst_cofins": M400Record._f(fields, 0),
            "vl_bc_cofins": M400Record._dec(M400Record._f(fields, 1)),
            "aliq_cofins_perc": M400Record._dec(M400Record._f(fields, 2)),
            "quant_bc_cofins": M400Record._dec(M400Record._f(fields, 3)),
            "aliq_cofins_real": M400Record._dec(M400Record._f(fields, 4)),
            "vl_cred": M400Record._dec(M400Record._f(fields, 5)),
            "vl_bc_cofins_ain": M400Record._dec(M400Record._f(fields, 6)),
            "aliq_cofins_ain": M400Record._dec(M400Record._f(fields, 7)),
            "vl_cred_ain": M400Record._dec(M400Record._f(fields, 8)),
            "vl_cred_desc": M400Record._dec(M400Record._f(fields, 9)),
            "vl_cred_desc_ain": M400Record._dec(M400Record._f(fields, 10)),
            "vl_cred_desc_pa_ant": M400Record._dec(M400Record._f(fields, 11)),
            "vl_cred_dispo": M400Record._dec(M400Record._f(fields, 12)),
            "vl_cred_isento": M400Record._dec(M400Record._f(fields, 13)),
            "vl_cred_desc_cumul": M400Record._dec(M400Record._f(fields, 14)),
        }


class M500Record(EFDContribRecord):
    """COFINS — total de contribuição apurada (M500)."""

    @staticmethod
    def parse(fields: List[str]) -> Dict[str, Any]:
        # M500 mirrors M200 structure for COFINS
        return {
            "record_type": "M500",
            "vl_tot_cont_nc_per": M500Record._dec(M500Record._f(fields, 0)),
            "vl_tot_cred_desc": M500Record._dec(M500Record._f(fields, 1)),
            "vl_tot_cred_desc_ain": M500Record._dec(M500Record._f(fields, 2)),
            "vl_tot_cred_desc_pa_ant": M500Record._dec(M500Record._f(fields, 3)),
            "vl_tot_cont_nc_dev": M500Record._dec(M500Record._f(fields, 4)),
            "vl_ret": M500Record._dec(M500Record._f(fields, 5)),
            "vl_out_ded": M500Record._dec(M500Record._f(fields, 6)),
            "vl_cont_dev_per": M500Record._dec(M500Record._f(fields, 7)),
            "vl_cont_ref_ant": M500Record._dec(M500Record._f(fields, 8)),
            "vl_tot_cont_cum": M500Record._dec(M500Record._f(fields, 9)),
            "vl_ret_nc": M500Record._dec(M500Record._f(fields, 10)),
            "vl_out_ded_nc": M500Record._dec(M500Record._f(fields, 11)),
            "vl_cont_dev_per_nc": M500Record._dec(M500Record._f(fields, 12)),
            "vl_cont_ref_ant_nc": M500Record._dec(M500Record._f(fields, 13)),
        }


class EFDContribuicoesParser:
    """Parser for EFD Contribuições (PIS/COFINS) files."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.warnings: List[str] = []

    def parse_bytes(self, raw: bytes) -> Dict[str, Any]:
        """Parse raw bytes with auto-detected encoding."""
        encoding = _detect_encoding(raw)
        try:
            content = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            content = raw.decode("latin-1", errors="replace")
            self.warnings.append(f"Encoding fallback to latin-1 (detected: {encoding})")
        return self.parse(content)

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse EFD Contribuições content string line-by-line.

        Returns:
            {
                "0000": {...},   # file header (cnpj, period, regime)
                "M100": [...],   # PIS credits per CST
                "M200": {...},   # PIS total apuração (single record per period)
                "M400": [...],   # COFINS credits per CST
                "M500": {...},   # COFINS total apuração
                "metadata": {...}
            }
        """
        if not content or not content.strip():
            raise EFDContribuicoesParseError("EFD Contribuições content is empty")

        self.warnings = []
        result: Dict[str, Any] = {
            "0000": {},
            "M100": [],
            "M200": None,
            "M400": [],
            "M500": None,
            "metadata": {},
        }

        line_num = 0
        for line_num, line in enumerate(content.split("\n"), start=1):
            line = line.strip()
            if not line:
                continue

            fields = line.split("|")

            if fields[0] == "" and len(fields) > 1:
                record_type = fields[1]
                offset = 1
            elif fields[0] != "":
                record_type = fields[0]
                offset = 0
            else:
                continue

            data_fields = fields[offset + 1:]

            try:
                if record_type == "0000":
                    result["0000"] = {
                        "cod_ver": data_fields[0] if data_fields else "",
                        "cod_fin": data_fields[1] if len(data_fields) > 1 else "",
                        "dt_ini": data_fields[2] if len(data_fields) > 2 else "",
                        "dt_fin": data_fields[3] if len(data_fields) > 3 else "",
                        "nome": data_fields[4] if len(data_fields) > 4 else "",
                        "cnpj": data_fields[5] if len(data_fields) > 5 else "",
                        "uf": data_fields[6] if len(data_fields) > 6 else "",
                        "ind_sit_esp": data_fields[9] if len(data_fields) > 9 else "",
                        "ind_nire": data_fields[10] if len(data_fields) > 10 else "",
                        "ind_inc_ativ": data_fields[11] if len(data_fields) > 11 else "",
                        "ind_metodo_apro_cred": data_fields[12] if len(data_fields) > 12 else "",
                        "cod_tipo_contrib": data_fields[13] if len(data_fields) > 13 else "",
                        "ind_reg_cum": data_fields[14] if len(data_fields) > 14 else "",
                    }
                elif record_type == "M100":
                    result["M100"].append(M100Record.parse(data_fields))
                elif record_type == "M200":
                    result["M200"] = M200Record.parse(data_fields)
                elif record_type == "M400":
                    result["M400"].append(M400Record.parse(data_fields))
                elif record_type == "M500":
                    result["M500"] = M500Record.parse(data_fields)

            except Exception as exc:
                self.warnings.append(f"Line {line_num}: failed to parse {record_type}: {exc}")
                logger.warning("Line %d: failed to parse %s: %s", line_num, record_type, exc)

        result["metadata"] = {
            "tenant_id": self.tenant_id,
            "total_m100_records": len(result["M100"]),
            "has_m200": result["M200"] is not None,
            "total_m400_records": len(result["M400"]),
            "has_m500": result["M500"] is not None,
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "warnings": self.warnings,
            "total_lines_processed": line_num,
        }

        return result
