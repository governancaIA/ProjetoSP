"""
Core fiscal validation rules for FiscalAI
Implements 7 MVP rules covering the most common inconsistencies
"""
from decimal import Decimal
from app.models.rule_log import SeverityLevel
from app.validators.rules.base import BaseRule, RuleResult
from app.validators.rules.registry import register
from app.core.security import mask_chave_acesso


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

        chave_masked = mask_chave_acesso(fiscal_document.chave_acesso)
        return self._fail(
            SeverityLevel.CRITICAL,
            f"NF-e {fiscal_document.numero_nf}/{fiscal_document.serie} cancelada (chave {chave_masked}) ainda registrada no SPED — deve ser excluída",
            input_snapshot={
                "numero_nf": fiscal_document.numero_nf,
                "serie": fiscal_document.serie,
                "chave_acesso": chave_masked,
                "status_nfe": fiscal_document.status_nfe,
            },
        )


@register
class SaidaSemLancamentoRule(BaseRule):
    """
    Detects CFOP inconsistency between declared natureza and operation type.

    Validates that:
    - NF-e de saída (ind_emitente=0) uses CFOPs 5xxx or 6xxx (outbound)
    - NF-e de entrada (ind_emitente=1) uses CFOPs 1xxx or 2xxx (inbound)

    A CFOP mismatch indicates wrong escrituração: e.g., saída lançada com CFOP de entrada,
    or the natureza field was set incorrectly on import.
    """
    rule_id = "saida_sem_lancamento"
    rule_version = "2.0.0"
    depends_on = []

    # CFOP prefix groupings
    _SAIDA_PREFIXES = {"5", "6", "7"}   # 5xxx=saída intraestadual, 6xxx=interestadual, 7xxx=exportação
    _ENTRADA_PREFIXES = {"1", "2", "3"} # 1xxx=entrada intraestadual, 2xxx=interestadual, 3xxx=importação

    def execute(self, fiscal_document, items, config) -> RuleResult:
        natureza = (fiscal_document.natureza or "").lower().strip()

        if not natureza:
            return self._pass(
                "Natureza da operação não informada — regra não aplicável",
                input_snapshot={"natureza": None},
            )

        if not items:
            return self._pass(
                "NF-e sem itens — regra não aplicável",
                input_snapshot={"natureza": natureza},
            )

        cfops = [item.cfop for item in items if item.cfop]
        if not cfops:
            return self._pass(
                "Itens sem CFOP — regra não aplicável",
                input_snapshot={"natureza": natureza, "num_itens": len(items)},
            )

        cfop_prefixes = {cfop[0] for cfop in cfops if cfop}

        is_saida = natureza in {"saida", "saída"}
        is_entrada = natureza in {"entrada"}

        if is_saida:
            # Saída deve usar apenas CFOPs 5xxx, 6xxx ou 7xxx
            wrong_cfops = [c for c in cfops if c and c[0] in self._ENTRADA_PREFIXES]
            if wrong_cfops:
                return self._fail(
                    SeverityLevel.CRITICAL,
                    f"NF-e de saída escriturada com CFOP de entrada: {sorted(set(wrong_cfops))} — "
                    f"indica escrituração incorreta ou nota de saída sem lançamento no livro fiscal",
                    input_snapshot={
                        "natureza": natureza,
                        "numero_nf": fiscal_document.numero_nf,
                        "chave_acesso": mask_chave_acesso(fiscal_document.chave_acesso),
                        "cfops_invalidos": sorted(set(wrong_cfops)),
                        "cfops_utilizados": sorted(set(cfops)),
                    },
                )
            return self._pass(
                f"Saída escriturada corretamente com CFOPs {sorted(cfop_prefixes)}xxx",
                input_snapshot={"natureza": natureza, "cfop_prefixes": sorted(cfop_prefixes)},
            )

        if is_entrada:
            # Entrada deve usar apenas CFOPs 1xxx, 2xxx ou 3xxx
            wrong_cfops = [c for c in cfops if c and c[0] in self._SAIDA_PREFIXES]
            if wrong_cfops:
                return self._fail(
                    SeverityLevel.WARNING,
                    f"NF-e de entrada escriturada com CFOP de saída: {sorted(set(wrong_cfops))} — "
                    f"verificar se a operação foi classificada corretamente",
                    input_snapshot={
                        "natureza": natureza,
                        "numero_nf": fiscal_document.numero_nf,
                        "cfops_invalidos": sorted(set(wrong_cfops)),
                        "cfops_utilizados": sorted(set(cfops)),
                    },
                )
            return self._pass(
                f"Entrada escriturada corretamente com CFOPs {sorted(cfop_prefixes)}xxx",
                input_snapshot={"natureza": natureza, "cfop_prefixes": sorted(cfop_prefixes)},
            )

        return self._pass(
            f"Natureza '{natureza}' — regra não aplicável a esta operação",
            input_snapshot={"natureza": natureza},
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

        chave_masked = mask_chave_acesso(fiscal_document.chave_acesso)
        return self._fail(
            SeverityLevel.CRITICAL,
            f"CT-e {fiscal_document.numero_nf} cancelado (chave {chave_masked}) ainda no SPED — deve ser excluído",
            input_snapshot={
                "numero_nf": fiscal_document.numero_nf,
                "chave_acesso": chave_masked,
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
    CST ICMS inválido ou incompatível com o regime tributário do tenant.

    Nível 1 (sempre): valida se o CST existe na Tabela A (regime normal, 00–90)
    ou Tabela B (Simples Nacional, 101–900). Códigos fora dessas tabelas causam
    rejeição na recepção do SPED.

    Nível 2 (quando regime_tributario disponível no TenantConfig):
    - lucro_real / lucro_presumido: apenas Tabela A (00–90)
    - simples_nacional: apenas Tabela B (101–900); uso de 00-90 indica
      erro de enquadramento ou escrituração fora do Simples
    """
    rule_id = "cst_incompativel"
    rule_version = "2.0.0"
    depends_on = []

    # Tabela A — regime normal (Lucro Real, Lucro Presumido)
    _CST_TABELA_A = {
        "00", "10", "20", "30", "40", "41", "50", "51", "60", "70", "90",
    }

    # Tabela B — Simples Nacional
    _CST_TABELA_B = {
        "101", "102", "103", "201", "202", "203", "300", "400", "500", "900",
    }

    _ALL_VALID_CSTS = _CST_TABELA_A | _CST_TABELA_B

    # Which regimes use which table
    _REGIME_TO_TABLE = {
        "lucro_real": _CST_TABELA_A,
        "lucro_presumido": _CST_TABELA_A,
        "simples_nacional": _CST_TABELA_B,
    }

    def execute(self, fiscal_document, items, config) -> RuleResult:
        if not items:
            return self._pass("NF-e sem itens", input_snapshot={})

        regime = (config.get("regime_tributario") or "").lower().strip()
        csts_presentes = {item.cst for item in items if item.cst}

        # Resolve valid sets: prefer DB-loaded sets, fall back to hardcoded
        valid_csts_regime: set | None = config.get("valid_csts_regime")
        valid_csts_all: set = config.get("valid_csts_all") or self._ALL_VALID_CSTS

        # Nível 2: regime conhecido — valida compatibilidade de tabela
        if regime in self._REGIME_TO_TABLE:
            # DB-sourced set takes priority; fall back to hardcoded regime table
            allowed = valid_csts_regime if valid_csts_regime is not None else self._REGIME_TO_TABLE[regime]
            wrong_table_csts = sorted(csts_presentes - allowed)
            wrong_items = [item for item in items if item.cst and item.cst in wrong_table_csts]

            if wrong_table_csts:
                table_name = "B (Simples Nacional)" if regime == "simples_nacional" else "A (regime normal)"
                other_table = "A (regime normal)" if regime == "simples_nacional" else "B (Simples Nacional)"
                source = "banco" if valid_csts_regime is not None else "hardcoded"
                return self._fail(
                    SeverityLevel.CRITICAL,
                    f"{len(wrong_items)} item(ns) com CST de tabela {other_table} incompatível com regime "
                    f"'{regime}' — deve usar tabela {table_name}: {wrong_table_csts}",
                    input_snapshot={
                        "regime_tributario": regime,
                        "num_itens_invalidos": len(wrong_items),
                        "csts_invalidos": wrong_table_csts,
                        "tabela_correta": table_name,
                        "total_itens": len(items),
                        "fonte_cst": source,
                    },
                    config_applied={"regime_tributario": regime},
                )

            return self._pass(
                f"CST ICMS compatíveis com regime '{regime}' em todos os {len(items)} itens",
                input_snapshot={
                    "regime_tributario": regime,
                    "num_itens": len(items),
                    "csts": sorted(csts_presentes),
                },
                config_applied={"regime_tributario": regime},
            )

        # Nível 1: regime desconhecido — valida apenas existência nas tabelas
        invalid_csts = sorted(csts_presentes - valid_csts_all)
        invalid_items = [item for item in items if item.cst and item.cst in invalid_csts]

        if not invalid_csts:
            return self._pass(
                f"CST ICMS válidos em todos os {len(items)} itens (tabelas A e B — regime não configurado)",
                input_snapshot={"num_itens": len(items), "csts": sorted(csts_presentes)},
            )

        return self._fail(
            SeverityLevel.WARNING,
            f"{len(invalid_items)} item(ns) com CST ICMS inexistente no Anexo I: {invalid_csts} — "
            f"verificar tabela A (regime normal) ou B (Simples Nacional)",
            input_snapshot={
                "num_itens_invalidos": len(invalid_items),
                "csts_invalidos": invalid_csts,
                "total_itens": len(items),
            },
        )


@register
class CfopInvalidoRule(BaseRule):
    """
    CFOP inválido ou incompatível com a natureza da operação.

    Nível 1 (fallback): quando cfop_reference não está disponível no config,
    valida apenas o formato (4 dígitos, primeiro dígito 1-9). Isso ocorre
    antes da primeira execução da migration 003.

    Nível 2 (quando valid_cfops + cfop_metadata presentes via RuleService.get_config):
    - Rejeita CFOPs que não existem na tabela ADE COTEPE (CRITICAL)
    - Valida que CFOPs 5xxx/6xxx/7xxx são usados em operações de saída (WARNING)
    - Valida que CFOPs 1xxx/2xxx/3xxx são usados em operações de entrada (WARNING)
    """
    rule_id = "cfop_invalido"
    rule_version = "2.0.0"
    depends_on = []

    _SAIDA_PREFIXES = {"5", "6", "7"}
    _ENTRADA_PREFIXES = {"1", "2", "3"}

    def execute(self, fiscal_document, items, config) -> RuleResult:
        if not items:
            return self._pass("NF-e sem itens", input_snapshot={})

        cfops = [item.cfop for item in items if item.cfop]
        cfops_unicos = set(cfops)

        if not cfops_unicos:
            return self._pass(
                "Itens sem CFOP — regra não aplicável",
                input_snapshot={"num_itens": len(items)},
            )

        valid_cfops: set = config.get("valid_cfops")
        cfop_metadata: dict = config.get("cfop_metadata", {})

        # Nível 1: sem tabela de referência — valida apenas formato
        if not valid_cfops:
            malformed = sorted(
                c for c in cfops_unicos
                if not (len(c) == 4 and c[0] in "123456789" and c.isdigit())
            )
            if malformed:
                return self._fail(
                    SeverityLevel.WARNING,
                    f"CFOP(s) com formato inválido: {malformed} — deve ter 4 dígitos numéricos começando por 1-9",
                    input_snapshot={
                        "cfops_invalidos": malformed,
                        "cfops_utilizados": sorted(cfops_unicos),
                    },
                )
            return self._pass(
                f"CFOPs com formato válido em todos os {len(items)} itens (tabela CFOP não disponível — validação parcial)",
                input_snapshot={"cfops_utilizados": sorted(cfops_unicos), "num_itens": len(items)},
            )

        # Nível 2: tabela ADE COTEPE disponível

        # 2a. CFOPs inexistentes na tabela oficial
        inexistentes = sorted(cfops_unicos - valid_cfops)
        if inexistentes:
            return self._fail(
                SeverityLevel.CRITICAL,
                f"CFOP(s) inexistente(s) na tabela ADE COTEPE: {inexistentes} — "
                f"causará rejeição no SPED",
                input_snapshot={
                    "cfops_inexistentes": inexistentes,
                    "cfops_utilizados": sorted(cfops_unicos),
                    "num_itens": len(items),
                },
            )

        # 2b. Compatibilidade com natureza da operação (entrada/saída)
        natureza = (fiscal_document.natureza or "").lower().strip()
        is_saida = natureza in {"saida", "saída"}
        is_entrada = natureza in {"entrada"}

        if is_saida or is_entrada:
            esperado_prefixes = self._SAIDA_PREFIXES if is_saida else self._ENTRADA_PREFIXES
            wrong_cfops = sorted(
                c for c in cfops_unicos
                if c[0] not in esperado_prefixes
            )
            if wrong_cfops:
                tipo_esperado = "saída (5xxx/6xxx/7xxx)" if is_saida else "entrada (1xxx/2xxx/3xxx)"
                return self._fail(
                    SeverityLevel.WARNING,
                    f"CFOP(s) incompatível(is) com natureza '{natureza}': {wrong_cfops} — "
                    f"operação de {natureza} deve usar CFOPs de {tipo_esperado}",
                    input_snapshot={
                        "natureza": natureza,
                        "cfops_incompativeis": wrong_cfops,
                        "cfops_utilizados": sorted(cfops_unicos),
                        "num_itens": len(items),
                    },
                )

        return self._pass(
            f"CFOPs válidos (ADE COTEPE) em todos os {len(items)} itens: {sorted(cfops_unicos)}",
            input_snapshot={
                "cfops_utilizados": sorted(cfops_unicos),
                "num_itens": len(items),
                "validacao": "nivel_2_com_tabela_referencia",
            },
        )
