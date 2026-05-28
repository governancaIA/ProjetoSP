"""
Anomaly detection rules for FiscalAI (Epic 3).
Uses statistical heuristics (Z-score, date checks) — no ML library required.

These rules consume pre-fetched historical data injected into config by
validate_document.py to avoid N+1 DB queries inside rule execution.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal

from app.models.rule_log import SeverityLevel
from app.validators.rules.base import BaseRule, RuleResult
from app.validators.rules.registry import register

_MIN_SAMPLES_ZSCORE = 5   # below this, skip Z-score (not enough data)
_ZSCORE_THRESHOLD = 3.0   # |z| > 3σ considered anomalous
_RETROACTIVITY_DAYS = 5   # data_emissao > N days before upload → WARNING
_FUTURE_DAYS = 1          # data_emissao > hoje + N dias → CRITICAL


@register
class ValorAnomalyRule(BaseRule):
    """
    Detects NF-e values that deviate >3σ from the historical mean for the
    same emitente_cnpj (Z-score anomaly detection).

    Requires config["supplier_valor_history"] — a dict mapping
    emitente_cnpj → list[float] of past valor_total values.

    Skips if fewer than MIN_SAMPLES historical documents exist (not enough data).
    Skips entirely for SPED documents (aggregate values make Z-score misleading).
    """
    rule_id = "valor_anomaly_zscore"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        if config.get("source_document_type") == "sped_efd_icms":
            return self._pass(
                "SPED: Z-score não aplicável a valores agregados do livro fiscal",
                input_snapshot={"source": "sped_efd_icms"},
            )

        history: dict[str, list[float]] = config.get("supplier_valor_history") or {}
        cnpj = fiscal_document.emitente_cnpj
        if not cnpj:
            return self._pass(
                "CNPJ do emitente não informado — anomalia de valor não verificável",
                input_snapshot={},
            )

        past_values = history.get(cnpj, [])
        if len(past_values) < _MIN_SAMPLES_ZSCORE:
            return self._pass(
                f"Histórico insuficiente para {cnpj[:6]}***CNPJ*** "
                f"({len(past_values)} docs < mínimo {_MIN_SAMPLES_ZSCORE}) — Z-score pulado",
                input_snapshot={"samples": len(past_values), "min_required": _MIN_SAMPLES_ZSCORE},
            )

        mean = statistics.mean(past_values)
        std = statistics.stdev(past_values)

        if std == 0:
            return self._pass(
                "Desvio padrão histórico = 0 — todos os valores são idênticos, sem anomalia detectável",
                input_snapshot={"mean": mean, "std": 0, "samples": len(past_values)},
            )

        valor = float(fiscal_document.valor_total or 0)
        z_score = abs(valor - mean) / std

        if z_score <= _ZSCORE_THRESHOLD:
            return self._pass(
                f"Valor R${valor:,.2f} dentro de {z_score:.1f}σ da média histórica "
                f"R${mean:,.2f} ({len(past_values)} docs analisados)",
                input_snapshot={"valor": valor, "mean": round(mean, 2), "std": round(std, 2),
                                "z_score": round(z_score, 2), "samples": len(past_values)},
            )

        direction = "acima" if valor > mean else "abaixo"
        return self._fail(
            SeverityLevel.WARNING,
            f"Valor R${valor:,.2f} é {z_score:.1f}σ {direction} da média histórica "
            f"R${mean:,.2f} deste fornecedor ({len(past_values)} docs) — possível nota atípica",
            input_snapshot={
                "valor_atual": valor,
                "media_historica": round(mean, 2),
                "desvio_padrao": round(std, 2),
                "z_score": round(z_score, 2),
                "samples": len(past_values),
                "threshold": _ZSCORE_THRESHOLD,
            },
            config_applied={"z_score_threshold": _ZSCORE_THRESHOLD, "min_samples": _MIN_SAMPLES_ZSCORE},
        )


@register
class SequenciaNotasRule(BaseRule):
    """
    Detects temporal anomalies in NF-e issuance:

    1. Data retroativa: document issued >N days before it was uploaded/processed.
       Indicates late escrituração or pre-dated invoices — common fraud pattern.

    2. Data futura: document dated after today.
       Indicates pre-issued invoice or system clock issue.

    Requires config["validation_date"] (date) — injected by validate_document.py.
    """
    rule_id = "sequencia_notas_temporal"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config) -> RuleResult:
        data_emissao = fiscal_document.data_emissao
        if not data_emissao:
            return self._pass(
                "Data de emissão não informada — verificação temporal não aplicável",
                input_snapshot={},
            )

        validation_date: date = config.get("validation_date") or date.today()

        # 1. Data futura
        if data_emissao > validation_date + timedelta(days=_FUTURE_DAYS):
            delta = (data_emissao - validation_date).days
            return self._fail(
                SeverityLevel.CRITICAL,
                f"NF-e emitida {delta} dia(s) no futuro (emissão: {data_emissao}, "
                f"processamento: {validation_date}) — nota pré-datada ou erro de sistema",
                input_snapshot={
                    "data_emissao": str(data_emissao),
                    "validation_date": str(validation_date),
                    "delta_days": delta,
                },
                config_applied={"future_threshold_days": _FUTURE_DAYS},
            )

        # 2. Data retroativa excessiva
        retroactivity = (validation_date - data_emissao).days
        if retroactivity > _RETROACTIVITY_DAYS:
            severity = SeverityLevel.CRITICAL if retroactivity > 30 else SeverityLevel.WARNING
            return self._fail(
                severity,
                f"NF-e escriturada com {retroactivity} dia(s) de atraso "
                f"(emissão: {data_emissao}, processamento: {validation_date}) — "
                f"{'possível fraude ou nota fantasma' if retroactivity > 30 else 'escrituração fora do prazo'}",
                input_snapshot={
                    "data_emissao": str(data_emissao),
                    "validation_date": str(validation_date),
                    "retroactivity_days": retroactivity,
                },
                config_applied={"retroactivity_threshold_days": _RETROACTIVITY_DAYS},
            )

        return self._pass(
            f"Data de emissão {data_emissao} dentro do prazo esperado "
            f"({retroactivity} dia(s) de antecedência ao processamento)",
            input_snapshot={
                "data_emissao": str(data_emissao),
                "validation_date": str(validation_date),
                "retroactivity_days": retroactivity,
            },
        )
