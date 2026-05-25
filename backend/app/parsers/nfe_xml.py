"""
NF-e XML Parser (US-1.6)

Parses NF-e XML v4.0 and extracts:
- Header info (chave_acesso, emitente, destinatario, datas)
- Item details with tax information (CFOP, CST, ICMS, PIS, COFINS, IPI)
- Totals and protocol information
- Cancelamento detection
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from lxml import etree
import logging

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when NF-e XML parsing fails"""
    pass


class NFEParser:
    """NF-e XML v4.0 parser"""

    def __init__(self, tenant_id: str):
        """Initialize parser for a specific tenant"""
        self.tenant_id = tenant_id
        self.warnings: List[str] = []

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse NF-e XML content

        Args:
            content: Full NF-e XML file content as string

        Returns:
            {
                "nfe": {...},      # header with status, protocolo, etc
                "itens": [...],    # item details with taxes
                "metadata": {...}  # parse stats
            }

        Raises:
            ParseError: If content is empty or invalid XML
        """
        if not content or not content.strip():
            raise ParseError("NF-e XML content is empty")

        self.warnings = []
        result = {
            "nfe": {},
            "itens": [],
            "metadata": {
                "tenant_id": self.tenant_id,
                "parsed_at": datetime.now(timezone.utc).isoformat(),
                "warnings": self.warnings,
                "total_itens": 0,
                "cancelado": False,
            }
        }

        try:
            root = etree.fromstring(content.encode('utf-8'))
            # Strip namespaces for simpler XPath
            root = self._strip_ns(root)

            # Find infNFe (the main NF-e document)
            inf_nfe = root.find('.//infNFe')
            if inf_nfe is None:
                raise ParseError("Invalid NF-e: no infNFe element found")

            # Parse sections
            self._parse_header(inf_nfe, result["nfe"])
            self._parse_itens(inf_nfe, result["itens"], result["metadata"])
            self._parse_totals(inf_nfe, result["nfe"])
            self._parse_protocolo(root, result["nfe"])

            # Check if canceled
            result["nfe"]["cancelado"] = result["nfe"].get("status") == "cancelado"
            result["metadata"]["cancelado"] = result["nfe"]["cancelado"]
            result["metadata"]["total_itens"] = len(result["itens"])

        except etree.XMLSyntaxError as e:
            raise ParseError(f"Invalid XML syntax: {str(e)}")
        except Exception as e:
            self.warnings.append(f"Parse error: {str(e)}")
            logger.warning(f"NF-e parse error: {str(e)}")
            raise ParseError(f"Failed to parse NF-e: {str(e)}")

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

    def _parse_header(self, inf_nfe: Any, nfe_dict: Dict[str, Any]) -> None:
        """Parse NF-e header (ide, emit, dest)"""
        # Extract chave_acesso from infNFe/@Id (format: NFe35180166047275000199550010000000011234567890)
        chave_attr = inf_nfe.get('Id', '')
        chave_acesso = chave_attr.replace('NFe', '') if chave_attr.startswith('NFe') else chave_attr

        nfe_dict["chave_acesso"] = chave_acesso
        nfe_dict["numero_nf"] = self._get_text(inf_nfe, 'ide/nNF')
        nfe_dict["serie"] = self._get_text(inf_nfe, 'ide/serie')

        # tpNF: 0=entrada, 1=saída
        tp_nf = self._get_text(inf_nfe, 'ide/tpNF')
        nfe_dict["natureza"] = "entrada" if tp_nf == "0" else "saída"

        # Emitter
        emit = inf_nfe.find('emit')
        nfe_dict["emitente_cnpj"] = self._get_text(emit, 'CNPJ') or self._get_text(emit, 'CPF', '')
        nfe_dict["emitente_nome"] = self._get_text(emit, 'xNome')

        # Recipient
        dest = inf_nfe.find('dest')
        if dest is not None:
            nfe_dict["destinatario_cnpj"] = self._get_text(dest, 'CNPJ') or self._get_text(dest, 'CPF', '')
            nfe_dict["destinatario_nome"] = self._get_text(dest, 'xNome')
        else:
            nfe_dict["destinatario_cnpj"] = ""
            nfe_dict["destinatario_nome"] = ""

        # Dates
        dh_emi = self._get_text(inf_nfe, 'ide/dhEmi') or self._get_text(inf_nfe, 'ide/dEmi')
        nfe_dict["data_emissao"] = self._parse_date(dh_emi)

        dh_sai = self._get_text(inf_nfe, 'ide/dhSaiEnt')
        nfe_dict["data_saida"] = self._parse_date(dh_sai) if dh_sai else nfe_dict["data_emissao"]

        # Referenced NF-e (for devoluções/complementares)
        nf_ref = inf_nfe.find('NFref/refNFe')
        nfe_dict["chave_acesso_referenciada"] = nf_ref.text if nf_ref is not None and nf_ref.text else None

    def _parse_itens(self, inf_nfe: Any, itens_list: List[Dict], metadata: Dict) -> None:
        """Parse NF-e items (det elements)"""
        det_list = inf_nfe.findall('det')

        for idx, det in enumerate(det_list, start=1):
            try:
                item = {}

                # Item sequence
                item["item_seq"] = int(det.get('nItem', idx))

                # Product details
                prod = det.find('prod')
                if prod is None:
                    self.warnings.append(f"Item {idx}: missing prod element")
                    continue

                item["codigo_produto"] = self._get_text(prod, 'cProd')
                item["descricao"] = self._get_text(prod, 'xProd')
                item["ncm"] = self._get_text(prod, 'NCM')
                item["cfop"] = self._get_text(prod, 'CFOP')

                # Quantity and unit
                item["quantidade"] = self._get_float(prod, 'qCom')
                item["unidade"] = self._get_text(prod, 'uCom')
                item["valor_unitario"] = self._get_float(prod, 'vUnCom')
                item["valor_item"] = self._get_float(prod, 'vProd')
                item["valor_desconto"] = self._get_float(prod, 'vDesc')

                # Taxes
                imposto = det.find('imposto')
                if imposto is not None:
                    icms_data = self._extract_icms(imposto)
                    item.update(icms_data)

                    pis_data = self._extract_pis(imposto)
                    item.update(pis_data)

                    cofins_data = self._extract_cofins(imposto)
                    item.update(cofins_data)

                    ipi_data = self._extract_ipi(imposto)
                    item.update(ipi_data)

                itens_list.append(item)

            except Exception as e:
                self.warnings.append(f"Item {idx}: parse failed: {str(e)}")
                logger.warning(f"Failed to parse NF-e item {idx}: {str(e)}")

    def _extract_icms(self, imposto: Any) -> Dict[str, Any]:
        """Extract ICMS tax data from item"""
        result = {
            "cst": "",
            "base_icms": 0.0,
            "aliquota_icms": 0.0,
            "valor_icms": 0.0,
        }

        icms_group = imposto.find('ICMS')
        if icms_group is None:
            return result

        # Find first ICMS variant (ICMS00, ICMS10, ICMS20, ICMS40, etc.)
        icms_el = None
        for child in icms_group:
            if child.tag and child.tag.startswith('ICMS'):
                icms_el = child
                break

        if icms_el is not None:
            # Try CST first (normal), then CSOSN (simples nacional)
            cst = icms_el.find('CST')
            if cst is None:
                cst = icms_el.find('CSOSN')

            if cst is not None:
                result["cst"] = cst.text.strip() if cst.text else ""

            result["base_icms"] = self._get_float(icms_el, 'vBC')
            result["aliquota_icms"] = self._get_float(icms_el, 'pICMS')
            result["valor_icms"] = self._get_float(icms_el, 'vICMS')

        return result

    def _extract_pis(self, imposto: Any) -> Dict[str, Any]:
        """Extract PIS tax data from item"""
        result = {
            "base_pis": 0.0,
            "aliquota_pis": 0.0,
            "valor_pis": 0.0,
        }

        pis_group = imposto.find('PIS')
        if pis_group is None:
            return result

        # Find first PIS variant (PISAliq, PISQtde, PISNT, etc.)
        pis_el = None
        for child in pis_group:
            if child.tag:
                pis_el = child
                break

        if pis_el is not None:
            result["base_pis"] = self._get_float(pis_el, 'vBC')
            result["aliquota_pis"] = self._get_float(pis_el, 'pPIS')
            result["valor_pis"] = self._get_float(pis_el, 'vPIS')

        return result

    def _extract_cofins(self, imposto: Any) -> Dict[str, Any]:
        """Extract COFINS tax data from item"""
        result = {
            "base_cofins": 0.0,
            "aliquota_cofins": 0.0,
            "valor_cofins": 0.0,
        }

        cofins_group = imposto.find('COFINS')
        if cofins_group is None:
            return result

        # Find first COFINS variant (COFINSAliq, COFINSQtde, COFINSNT, etc.)
        cofins_el = None
        for child in cofins_group:
            if child.tag:
                cofins_el = child
                break

        if cofins_el is not None:
            result["base_cofins"] = self._get_float(cofins_el, 'vBC')
            result["aliquota_cofins"] = self._get_float(cofins_el, 'pCOFINS')
            result["valor_cofins"] = self._get_float(cofins_el, 'vCOFINS')

        return result

    def _extract_ipi(self, imposto: Any) -> Dict[str, Any]:
        """Extract IPI tax data from item"""
        result = {
            "valor_ipi": 0.0,
        }

        ipi = imposto.find('IPI')
        if ipi is None:
            return result

        # Find first IPI variant
        ipi_el = None
        for child in ipi:
            if child.tag:
                ipi_el = child
                break

        if ipi_el is not None:
            result["valor_ipi"] = self._get_float(ipi_el, 'vIPI')

        return result

    def _parse_totals(self, inf_nfe: Any, nfe_dict: Dict[str, Any]) -> None:
        """Parse NF-e totals"""
        total_el = inf_nfe.find('total/ICMSTot')
        if total_el is not None:
            nfe_dict["valor_total"] = self._get_float(total_el, 'vNF')
            nfe_dict["valor_icms"] = self._get_float(total_el, 'vICMS')
            nfe_dict["valor_pis"] = self._get_float(total_el, 'vPIS')
            nfe_dict["valor_cofins"] = self._get_float(total_el, 'vCOFINS')
            nfe_dict["valor_ipi"] = self._get_float(total_el, 'vIPI')
        else:
            nfe_dict["valor_total"] = 0.0
            nfe_dict["valor_icms"] = 0.0
            nfe_dict["valor_pis"] = 0.0
            nfe_dict["valor_cofins"] = 0.0
            nfe_dict["valor_ipi"] = 0.0

    def _parse_protocolo(self, root: Any, nfe_dict: Dict[str, Any]) -> None:
        """Parse protocol and authorization info"""
        prot_nfe = root.find('.//protNFe/infProt')

        if prot_nfe is not None:
            c_stat = self._get_text(prot_nfe, 'cStat')
            nfe_dict["status"] = self._map_status(c_stat)
            nfe_dict["protocolo"] = self._get_text(prot_nfe, 'nProt')

            dh_recbto = self._get_text(prot_nfe, 'dhRecbto')
            nfe_dict["data_autorizacao"] = self._parse_date(dh_recbto)
        else:
            nfe_dict["status"] = "desconhecido"
            nfe_dict["protocolo"] = ""
            nfe_dict["data_autorizacao"] = ""

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
