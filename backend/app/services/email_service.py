"""
Email alert service — dispara notificações de alertas CRÍTICOS por SMTP.
Só executa se SMTP_HOST, SMTP_USER e ALERT_EMAIL_TO estiverem configurados.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_critical_alert_email(
    tenant_id: str,
    document_id: int,
    original_filename: str,
    critical_alerts: list[dict[str, Any]],
) -> bool:
    """
    Envia email com os alertas CRÍTICOS de um documento processado.

    Args:
        tenant_id: ID do tenant (empresa)
        document_id: ID do documento processado
        original_filename: Nome original do arquivo enviado
        critical_alerts: Lista de dicts com keys: rule_id, message, exposure

    Returns:
        True se enviado com sucesso, False se desabilitado ou com erro.
    """
    if not settings.email_enabled:
        return False

    brand = settings.BRAND_NAME or "FiscalAI"
    recipients = [r.strip() for r in settings.ALERT_EMAIL_TO.split(",") if r.strip()]
    if not recipients:
        return False

    total_exposure = sum(a.get("exposure", 0) for a in critical_alerts)
    n = len(critical_alerts)

    subject = f"[{brand}] {n} alerta(s) CRÍTICO(s) — {original_filename}"

    # Plain text
    rows_txt = "\n".join(
        f"  • {a['rule_id']}: {a.get('message', '')} (exposição estimada: R$ {a.get('exposure', 0):,.2f})"
        for a in critical_alerts
    )
    text_body = (
        f"Alerta Fiscal — {brand}\n"
        f"{'=' * 50}\n\n"
        f"Arquivo processado: {original_filename}\n"
        f"Tenant: {tenant_id}\n"
        f"Documento ID: {document_id}\n\n"
        f"Foram detectados {n} alerta(s) CRÍTICO(s):\n\n"
        f"{rows_txt}\n\n"
        f"Exposição total estimada: R$ {total_exposure:,.2f}\n\n"
        f"Acesse a plataforma para detalhes e ações corretivas.\n"
    )

    # HTML
    rows_html = "".join(
        f"<tr>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #fecaca;font-family:monospace;font-size:13px'>{a['rule_id']}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #fecaca;font-size:13px'>{a.get('message', '')}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #fecaca;font-size:13px;text-align:right;font-weight:600;color:#dc2626'>"
        f"R$ {a.get('exposure', 0):,.2f}</td>"
        f"</tr>"
        for a in critical_alerts
    )
    html_body = f"""
<html><body style="font-family:sans-serif;color:#1e293b;margin:0;padding:0">
<div style="max-width:640px;margin:32px auto;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden">
  <div style="background:#1e3a5f;padding:20px 24px">
    <h1 style="margin:0;color:#fff;font-size:20px">{brand}</h1>
    <p style="margin:4px 0 0;color:#94a3b8;font-size:13px">Notificação de Alertas Fiscais</p>
  </div>
  <div style="padding:24px">
    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:12px 16px;margin-bottom:20px">
      <strong style="color:#dc2626">⚠ {n} alerta(s) CRÍTICO(s) detectado(s)</strong><br/>
      <span style="font-size:13px;color:#64748b">Arquivo: <b>{original_filename}</b></span>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead>
        <tr style="background:#f8fafc">
          <th style="padding:8px 12px;text-align:left;font-size:12px;color:#64748b;border-bottom:2px solid #e2e8f0">Regra</th>
          <th style="padding:8px 12px;text-align:left;font-size:12px;color:#64748b;border-bottom:2px solid #e2e8f0">Inconsistência</th>
          <th style="padding:8px 12px;text-align:right;font-size:12px;color:#64748b;border-bottom:2px solid #e2e8f0">Exposição Est.</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p style="margin-top:16px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:13px;color:#64748b">
      Exposição total estimada: <strong style="color:#dc2626">R$ {total_exposure:,.2f}</strong>
    </p>
  </div>
  <div style="background:#f8fafc;padding:12px 24px;font-size:12px;color:#94a3b8;text-align:center">
    Gerado por {brand} · Acesse a plataforma para detalhes e ações corretivas.
  </div>
</div>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, recipients, msg.as_string())
        logger.info(
            "Critical alert email sent",
            extra={"tenant_id": tenant_id, "document_id": document_id, "recipients": len(recipients)},
        )
        return True
    except Exception as exc:
        logger.warning(
            "Failed to send critical alert email: %s",
            exc,
            extra={"tenant_id": tenant_id, "document_id": document_id},
        )
        return False
