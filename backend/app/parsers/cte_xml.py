"""
CT-e XML Parser (US-1.7)

Parses CT-e XML v3.0 and extracts:
- Header info (chave_acesso, transportador, remetente, destinatario)
- Transport details (data, natureza, valor)
- Status and protocol information
- Cancelamento detection
"""
from typing import Dict, List, Any
from datetime import datetime, timezone
from lxml import etree
import logging

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when CT-e XML parsing fails"""
    pass


class CTEParser:
    """CT-e XML v3.0 parser"""

    def __init__(self, tenant_id: str):
        """Initialize parser for a specific tenant"""
        self.tenant_id = tenant_id
        self.warnings: List[str] = []

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse CT-e XML content

        Args:
            content: Full CT-e XML file content as string

        Returns:
            {
                "cte": {...},      # header with status, protocolo, etc
                "metadata": {...}  # parse stats
            }

        Raises:
            ParseError: If content is empty or invalid XML
        """
        if not content or not content.strip():
            raise ParseError("CT-e XML content is empty")

        self.warnings = []
        result = {
            "cte": {},
            "metadata": {
                "tenant_id": self.tenant_id,
                "parsed_at": datetime.now(timezone.utc).isoformat(),
                "warnings": self.warnings,
                "cancelado": False,
            }
        }

        try:
            root = etree.fromstring(content.encode('utf-8'))
            # Strip namespaces for simpler XPath
            root = self._strip_ns(root)

            # Find infCte (the main CT-e document)
            inf_cte = root.find('.//infCte')
            if inf_cte is None:
                raise ParseError("Invalid CT-e: no infCte element found")

            # Parse sections
            self._parse_header(inf_cte, result["cte"])
            self._parse_transport(inf_cte, result["cte"])
            self._parse_totals(inf_cte, result["cte"])
            self._parse_protocolo(root, result["cte"])

            # Check if canceled
            result["cte"]["cancelado"] = result["cte"].get("status") == "cancelado"
            result["metadata"]["cancelado"] = result["cte"]["cancelado"]

        except etree.XMLSyntaxError as e:
            raise ParseError(f"Invalid XML syntax: {str(e)}")
        except Exception as e:
            self.warnings.append(f"Parse error: {str(e)}")
            logger.warning(f"CT-e parse error: {str(e)}")
            raise ParseError(f"Failed to parse CT-e: {str(e)}")

        return result

    @staticmethod
    def _strip_ns(root):
        """Strip XML namespaces for simpler XPath navigation"""
        for el in root.iter():
            if el.tag and el.tag.startswith('{'):
                el.tag = el.tag.split('}', 1)[1]
        return root

    def _get_text(self, el: Any, xpath: str, default: str = "") -> str:
        """Safely extract text from XML element"""
        if el is None:
            return default
        try:
            found = el.find(xpath)
            if found is not None and found.text:
                return found.text.strip()
            return default
        except Exception:
            return default

    def _get_float(self, el: Any, xpath: str, default: float = 0.0) -> float:
        """Safely extract float from XML element"""
        text = self._get_text(el, xpath)
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default

    def _parse_date(self, date_str: str) -> str:
        """Parse ISO datetime and return as YYYY-MM-DD"""
        if not date_str:
            return ""
        try:
            # Handle both formats: 2018-01-15T10:30:00-03:00 and 2018-01-15
            if 'T' in date_str:
                # ISO datetime format
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
            else:
                # Plain date format
                return date_str[:10]
        except Exception:
            return date_str[:10] if date_str else ""

    def _parse_header(self, inf_cte: Any, cte_dict: Dict[str, Any]) -> None:
        """Parse CT-e header (ide, emit, rem, dest)"""
        # Extract chave_acesso from infCte/@Id (format: CTe35180166047275000199570010000000011234567890)
        chave_attr = inf_cte.get('Id', '')
        chave_acesso = chave_attr.replace('CTe', '') if chave_attr.startswith('CTe') else chave_attr

        cte_dict["chave_acesso"] = chave_acesso
        cte_dict["numero_cte"] = self._get_text(inf_cte, 'ide/nCT')
        cte_dict["serie"] = self._get_text(inf_cte, 'ide/serie')

        # Emitter (transportador)
        emit = inf_cte.find('emit')
        cte_dict["transportador_cnpj"] = self._get_text(emit, 'CNPJ') or self._get_text(emit, 'CPF', '')
        cte_dict["transportador_nome"] = self._get_text(emit, 'xNome')

        # Shipper (remetente)
        rem = inf_cte.find('rem')
        if rem is not None:
            cte_dict["remetente_cnpj"] = self._get_text(rem, 'CNPJ') or self._get_text(rem, 'CPF', '')
        else:
            cte_dict["remetente_cnpj"] = ""

        # Recipient (destinatário)
        dest = inf_cte.find('dest')
        if dest is not None:
            cte_dict["destinatario_cnpj"] = self._get_text(dest, 'CNPJ') or self._get_text(dest, 'CPF', '')
        else:
            cte_dict["destinatario_cnpj"] = ""

        # Date
        dh_emi = self._get_text(inf_cte, 'ide/dhEmi') or self._get_text(inf_cte, 'ide/dEmi')
        cte_dict["data_emissao"] = self._parse_date(dh_emi)

    def _parse_transport(self, inf_cte: Any, cte_dict: Dict[str, Any]) -> None:
        """Parse CT-e transport details"""
        cte_dict["natureza_operacao"] = self._get_text(inf_cte, 'ide/natOp')

    def _parse_totals(self, inf_cte: Any, cte_dict: Dict[str, Any]) -> None:
        """Parse CT-e totals"""
        # Valor do transporte (prestação de serviço)
        v_prest = inf_cte.find('vPrest')
        if v_prest is not None:
            cte_dict["valor_total"] = self._get_float(v_prest, 'vTPrest')
        else:
            cte_dict["valor_total"] = 0.0

        # ICMS value
        imp = inf_cte.find('imp')
        if imp is not None:
            icms = imp.find('ICMS')
            if icms is not None:
                # Find first ICMS variant
                icms_el = None
                for child in icms:
                    if child.tag and child.tag.startswith('ICMS'):
                        icms_el = child
                        break

                if icms_el is not None:
                    cte_dict["valor_icms"] = self._get_float(icms_el, 'vICMS')
                else:
                    cte_dict["valor_icms"] = 0.0
            else:
                cte_dict["valor_icms"] = 0.0
        else:
            cte_dict["valor_icms"] = 0.0

    def _parse_protocolo(self, root: Any, cte_dict: Dict[str, Any]) -> None:
        """Parse protocol and authorization info"""
        prot_cte = root.find('.//protCTe/infProt')

        if prot_cte is not None:
            c_stat = self._get_text(prot_cte, 'cStat')
            cte_dict["status"] = self._map_status(c_stat)
            cte_dict["protocolo"] = self._get_text(prot_cte, 'nProt')

            dh_recbto = self._get_text(prot_cte, 'dhRecbto')
            cte_dict["data_autorizacao"] = self._parse_date(dh_recbto)
        else:
            cte_dict["status"] = "desconhecido"
            cte_dict["protocolo"] = ""
            cte_dict["data_autorizacao"] = ""

    @staticmethod
    def _map_status(c_stat: str) -> str:
        """Map cStat code to status string"""
        status_map = {
            "100": "autorizado",
            "101": "cancelado",
            "102": "cancelado",
            "103": "denegado",
            "104": "denegado",
            "105": "denegado",
            "110": "desconhecido",
            "111": "desconhecido",
        }
        return status_map.get(c_stat, "desconhecido")
