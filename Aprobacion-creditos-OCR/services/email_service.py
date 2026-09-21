"""
Email Service — DemoBank Loan Application Asset
Sends decision notification emails via Gmail SMTP (port 587, STARTTLS).
Credentials are read from GMAIL_USER and GMAIL_APP_PASSWORD env vars.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

_GMAIL_USER     = os.getenv("GMAIL_USER", "")
_GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# ---------------------------------------------------------------------------
#  HTML email templates
# ---------------------------------------------------------------------------

_STYLE = """
  font-family: Arial, sans-serif;
  color: #1f2328;
  max-width: 580px;
  margin: 0 auto;
  padding: 24px;
"""

_HEADER_APROBAR  = "#15803d"
_HEADER_ESPERAR  = "#b45309"
_HEADER_RECHAZAR = "#b91c1c"


def _build_html(nombre: str, decision: str, resumen: str, razones: list[str]) -> str:
    decision_up = decision.upper()

    if decision_up == "APROBAR":
        header_color = _HEADER_APROBAR
        titulo       = "¡Felicitaciones! Tu solicitud fue aprobada"
        intro        = (
            f"Estimado/a <strong>{nombre}</strong>, nos complace informarte que tu solicitud "
            "de crédito hipotecario ha sido <strong>aprobada</strong>. "
            "En breve un asesor de DemoBank se pondrá en contacto para coordinar los próximos pasos."
        )
        cierre = (
            "Gracias por confiar en DemoBank para el financiamiento de tu hogar."
        )

    elif decision_up == "RECHAZAR":
        header_color = _HEADER_RECHAZAR
        titulo       = "Resultado de tu solicitud hipotecaria"
        intro        = (
            f"Estimado/a <strong>{nombre}</strong>, lamentamos informarte que en este momento "
            "tu solicitud de crédito hipotecario <strong>no puede ser aprobada</strong> "
            "según los criterios de evaluación vigentes."
        )
        cierre = (
            "Si considerás que hay información adicional que podría cambiar esta evaluación, "
            "podés contactarnos para presentar nueva documentación. "
            "DemoBank quiere acompañarte en el camino a tu casa propia."
        )

    else:  # ESPERAR
        header_color = _HEADER_ESPERAR
        titulo       = "Tu solicitud está en revisión"
        intro        = (
            f"Estimado/a <strong>{nombre}</strong>, tu solicitud de crédito hipotecario "
            "se encuentra actualmente <strong>en proceso de revisión</strong> por nuestro equipo. "
            "Te notificaremos con el resultado final a la brevedad."
        )
        cierre = (
            "Agradecemos tu paciencia. DemoBank trabaja para darte "
            "la mejor respuesta posible."
        )

    razones_html = ""
    if razones:
        items = "".join(f"<li style='margin-bottom:6px;'>{r}</li>" for r in razones)
        razones_html = f"""
        <p style="margin-top:18px;font-weight:600;">Observaciones del análisis:</p>
        <ul style="padding-left:20px;line-height:1.7;">{items}</ul>
        """

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>{titulo}</title></head>
<body style="background:#f5f6fa;padding:32px 0;">
  <div style="{_STYLE}background:#fff;border-radius:8px;border:1px solid #e5e7eb;">
    <div style="background:{header_color};color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;">
      <h2 style="margin:0;font-size:1.1rem;">HomeLoan — DemoBank</h2>
      <p  style="margin:6px 0 0;font-size:0.9rem;opacity:0.9;">Sistema de Asistencia a la Evaluación Crediticia</p>
    </div>
    <div style="padding:24px;">
      <h3 style="color:{header_color};margin-top:0;">{titulo}</h3>
      <p style="line-height:1.7;">{intro}</p>
      <p style="line-height:1.7;color:#57606a;font-style:italic;">{resumen}</p>
      {razones_html}
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="line-height:1.7;">{cierre}</p>
      <p style="margin-top:24px;color:#57606a;font-size:0.82rem;">
        Este mensaje fue generado automáticamente por el sistema HomeLoan.<br>
        Por favor no respondas a este correo — para consultas escribí a <a href="mailto:creditos@example.com">creditos@example.com</a>.
      </p>
    </div>
    <div style="background:#f7f8fa;padding:12px 24px;border-radius:0 0 8px 8px;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:0.78rem;color:#57606a;text-align:center;">
        DemoBank &copy; 2026 — HomeLoan Crédito Hipotecario
      </p>
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
#  Public entry point
# ---------------------------------------------------------------------------

def send_decision_email(
    persona: dict,
    decision: str,
    ai_result: dict,
) -> dict:
    """
    Send a decision email for the given persona.

    Args:
        persona:   Full persona dict from mock_data.get_persona_by_index().
        decision:  'aprobar' | 'esperar' | 'rechazar'
        ai_result: The full extraction result dict (used for resumen/razones).

    Returns:
        dict with keys 'ok' (bool) and 'error' (str, only on failure).
    """
    to_email = persona.get("email", "")
    nombre   = persona["renaper"]["nombre_completo"]
    rec      = ai_result.get("recomendacion", {})
    resumen  = rec.get("resumen", "")
    razones  = rec.get("razones", [])

    decision_up = decision.upper()
    subject_map = {
        "APROBAR":  "✅ Tu solicitud hipotecaria fue aprobada — DemoBank",
        "ESPERAR":  "⏳ Tu solicitud está en revisión — DemoBank",
        "RECHAZAR": "📋 Resultado de tu solicitud hipotecaria — DemoBank",
    }
    subject = subject_map.get(decision_up, "Resultado de tu solicitud — DemoBank")

    html_body = _build_html(nombre, decision, resumen, razones)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = _GMAIL_USER
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(_GMAIL_USER, _GMAIL_PASSWORD)
            server.sendmail(_GMAIL_USER, [to_email], msg.as_string())
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
