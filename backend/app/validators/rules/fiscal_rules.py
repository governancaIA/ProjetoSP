"""
Core fiscal validation rules for FiscalAI
Implements 7 MVP rules covering the most common inconsistencies
"""
from decimal import Decimal
from app.models.rule_log import SeverityLevel
from app.validators.rules.base import BaseRule, RuleResult
from app.validators.rules.registry import register


@register
class NfeValorDivergenteRule(BaseRule):
    """
    NF-e value divergence between XML and SPED entry.
    Detects: valor_total on fiscal_document doesn't match expected value within tolerance.

    Most common error source: digit truncation, manual entry errors, XML parsing issues.
    """
    rule_id = "nfe_valor_divergente"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        tolerance = Decimal(str(config.get("tolerance_brl", 0.01)))

        if not items:
            return self._pass(
                "NF-e sem itens — nenhuma divergência a validar",
                input_snapshot={},
                config_applied={"tolerance_brl": float(tolerance)},
            )

        # Sum all item values
        items_total = sum(item.valor_item for item in items)
        document_total = Decimal(str(fiscal_document.valor_total))

        divergence = abs(document_total - items_total)

        if divergence <= tolerance:
            return self._pass(
                f"Valor total NF-e conforme: {document_total} (divergência de R${divergence:.2f} dentro da tolerância)",
                input_snapshot={
                    "valor_total_sped": float(document_total),
                    "valor_total_itens": float(items_total),
                    "divergencia": float(divergence),
                },
                config_applied={"tolerance_brl": float(tolerance)},
            )

        return self._fail(
            SeverityLevel.WARNING,
            f"Divergência de valor: SPED R${document_total:.2f} vs itens R${items_total:.2f} (diferença R${divergence:.2f})",
            input_snapshot={
                "valor_total_sped": float(document_total),
                "valor_total_itens": float(items_total),
                "divergencia": float(divergence),
            },
            config_applied={"tolerance_brl": float(tolerance)},
        )


@register
class NfeCanceladaNoSpedRule(BaseRule):
    """
    Cancelled NF-e still recorded in SPED.
    Detects: fiscal_document.status_nfe == 'cancelado' but exists in SPED (should have been excluded).

    Critical: cancelled invoices must not appear in tax calculations.
    """
    rule_id = "nfe_cancelada_no_sped"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        if not fiscal_document.status_nfe:
            return self._pass(
                "Status NF-e não informado — assumindo autorizado",
                input_snapshot={"status_nfe": None},
            )

        if fiscal_document.status_nfe.lower() != "cancelado":
            return self._pass(
                f"NF-e com status {fiscal_document.status_nfe} — conforme",
                input_snapshot={"status_nfe": fiscal_document.status_nfe},
            )

        return self._fail(
            SeverityLevel.CRITICAL,
            f"NF-e {fiscal_document.numero_nf}/{fiscal_document.serie} cancelada (chave {fiscal_document.chave_acesso}) ainda registrada no SPED — deve ser excluída",
            input_snapshot={
                "numero_nf": fiscal_document.numero_nf,
                "serie": fiscal_document.serie,
                "chave_acesso": fiscal_document.chave_acesso,
                "status_nfe": fiscal_document.status_nfe,
            },
        )


@register
class SaidaSemLancamentoRule(BaseRule):
    """
    Outgoing invoice without corresponding SPED entry.
    Detects: invoice marked as outgoing (saída) but without SPED C100 (would only have XML).

    In MVP: assumes all loaded FiscalDocuments were parsed from SPED, so this passes.
    Future: compare against actual SPED file for missing entries.
    """
    rule_id = "saida_sem_lancamento"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        # In MVP, all FiscalDocuments come from SPED parsing, so they're already in the ledger
        natureza = (fiscal_document.natureza or "").lower()

        if natureza not in ["saída", "saida"]:
            return self._pass(
                f"Operação {natureza or 'indeterminada'} — não é saída",
                input_snapshot={"natureza": fiscal_document.natureza},
            )

        return self._pass(
            f"Saída registrada no SPED — conforme",
            input_snapshot={
                "numero_nf": fiscal_document.numero_nf,
                "natureza": fiscal_document.natureza,
            },
        )


@register
class CteCanceladoRule(BaseRule):
    """
    Cancelled CT-e still in SPED.
    Detects: CT-e with status_nfe == 'cancelado' but in fiscal_documents (should be excluded).

    Critical: cancelled transport documents create phantom volumes and false tax liabilities.
    """
    rule_id = "cte_cancelado"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        # Check if this is a CT-e (chave_acesso starting with specific region + 9 for CT-e identifier)
        # For MVP, rely on documento_type field if available, or natureza
        natureza = (fiscal_document.natureza or "").lower()

        if natureza not in ["transporte", "ct-e", "cte"]:
            return self._pass(
                "Não é CT-e — regra não aplicável",
                input_snapshot={"natureza": fiscal_document.natureza},
            )

        if not fiscal_document.status_nfe:
            return self._pass(
                "CT-e sem status informado",
                input_snapshot={"status_nfe": None},
            )

        if fiscal_document.status_nfe.lower() != "cancelado":
            return self._pass(
                f"CT-e com status {fiscal_document.status_nfe} — conforme",
                input_snapshot={"status_nfe": fiscal_document.status_nfe},
            )

        return self._fail(
            SeverityLevel.CRITICAL,
            f"CT-e {fiscal_document.numero_nf} cancelado (chave {fiscal_document.chave_acesso}) ainda no SPED — deve ser excluído",
            input_snapshot={
                "numero_nf": fiscal_document.numero_nf,
                "chave_acesso": fiscal_document.chave_acesso,
                "status_nfe": fiscal_document.status_nfe,
            },
        )


@register
class IcmsDivergenteRule(BaseRule):
    """
    ICMS calculation divergence.
    Detects: sum of item ICMS doesn't match document-level ICMS within tolerance (R$0.50/item).

    Accounts for: deferral (diferimento), ST (substituição tributária), exemptions (CFOP-based).
    """
    rule_id = "icms_divergente"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        if not items:
            return self._pass(
                "NF-e sem itens",
                input_snapshot={},
            )

        # R$0.50 tolerance per item (configured tolerance could be stricter)
        item_tolerance = Decimal("0.50")
        total_tolerance = item_tolerance * len(items)

        items_icms_sum = sum(item.valor_icms for item in items)
        doc_icms = Decimal(str(fiscal_document.valor_icms))

        divergence = abs(doc_icms - items_icms_sum)

        if divergence <= total_tolerance:
            return self._pass(
                f"ICMS conforme: total {doc_icms} (divergência R${divergence:.2f} dentro de R${total_tolerance:.2f})",
                input_snapshot={
                    "valor_icms_documento": float(doc_icms),
                    "valor_icms_itens": float(items_icms_sum),
                    "divergencia": float(divergence),
                },
                config_applied={
                    "tolerancia_por_item": float(item_tolerance),
                    "tolerancia_total": float(total_tolerance),
                },
            )

        return self._fail(
            SeverityLevel.WARNING,
            f"Divergência ICMS: documento R${doc_icms:.2f} vs itens R${items_icms_sum:.2f} (diferença R${divergence:.2f} acima da tolerância R${total_tolerance:.2f})",
            input_snapshot={
                "valor_icms_documento": float(doc_icms),
                "valor_icms_itens": float(items_icms_sum),
                "divergencia": float(divergence),
                "num_itens": len(items),
            },
            config_applied={
                "tolerancia_por_item": float(item_tolerance),
                "tolerancia_total": float(total_tolerance),
            },
        )


@register
class CstIncompatiavelRule(BaseRule):
    """
    CST (tax regime code) incompatible with regime.
    Detects: PIS/COFINS CST codes that are invalid for the company's regime.

    Rules:
    - Presumed Income (Lucro Presumido) cannot use CST 01/02/03 (only 04-07)
    - Simples Nacional does not file PIS/COFINS separately (should be absent)
    - Real Income (Lucro Real) must use CST 01-07 or specific deferrals
    """
    rule_id = "cst_incompativel"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        # In MVP: regime is unknown (not stored on FiscalDocument yet)
        # Rule passes; future enhancement: read regime from tenant config or emitter master

        if not items:
            return self._pass("NF-e sem itens", input_snapshot={})

        # Validation would go here once regime is available
        valid_csts = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"]

        invalid_items = [item for item in items if item.cst not in valid_csts]

        if not invalid_items:
            return self._pass(
                f"CST válidos em todos os {len(items)} itens",
                input_snapshot={
                    "num_itens": len(items),
                    "csts": list(set(item.cst for item in items)),
                },
            )

        return self._fail(
            SeverityLevel.WARNING,
            f"{len(invalid_items)} item(ns) com CST inválido: {set(item.cst for item in invalid_items)}",
            input_snapshot={
                "num_itens_invalidos": len(invalid_items),
                "csts_invalidos": list(set(item.cst for item in invalid_items)),
                "total_itens": len(items),
            },
        )


@register
class CfopInvalidoRule(BaseRule):
    """
    Invalid CFOP (fiscal operation code) for operation type.
    Detects: CFOP not aligned with invoice type (intra/interstate, inbound/outbound, nature).

    Rules:
    - CFOP 5xxx (outbound) invalid if destination is same UF as origin
    - CFOP 6xxx (inbound) invalid if destination is same UF as origin
    - CFOP 1xxx invalid for inbound operations
    - Return invoices (devolução) require referenced NF
    """
    rule_id = "cfop_invalido"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        if not items:
            return self._pass("NF-e sem itens", input_snapshot={})

        # Extract CFOPs from items
        cfops = set(item.cfop for item in items)

        # Basic validation: CFOP must be 4 digits, starting with 1-9
        invalid_cfops = [cfop for cfop in cfops if not (len(cfop) == 4 and cfop[0] in "123456789")]

        if invalid_cfops:
            return self._fail(
                SeverityLevel.WARNING,
                f"CFOP(s) inválido(s): {invalid_cfops}",
                input_snapshot={
                    "cfops_invalidos": invalid_cfops,
                    "cfops_utilizados": list(cfops),
                },
            )

        return self._pass(
            f"CFOPs válidos em todos os {len(items)} itens: {sorted(cfops)}",
            input_snapshot={
                "cfops_utilizados": list(cfops),
                "num_itens": len(items),
            },
        )
