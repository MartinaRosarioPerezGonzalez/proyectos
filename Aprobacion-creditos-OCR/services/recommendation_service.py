"""
Recommendation Service — DemoBank Loan Application Asset
Produces a hybrid loan recommendation from already-normalised extraction data.

Decision hierarchy (deterministic — no LLM involved at this layer):
  RECHAZAR  ← any hard blocker (missing critical doc, identity mismatch, old recibo,
              income below absolute floor, cuota exceeds max ratio)
  REVISAR   ← any soft concern (income below preferred threshold, missing optional
              fields, low-confidence identity validation, declining salary trend)
  APROBAR   ← all hard checks pass and income meets the preferred threshold

Multi-recibo support:
  When haberes_historico is present (2+ recibos), the engine uses promedio_neto_pesos
  as the reference income figure instead of the single sueldo_neto field.
  Tendencia "decreciente" adds a soft concern (REVISAR).
  Consistencia "ALERTA" (different employer across recibos) adds a soft concern.

The engine never makes a final credit decision on its own.
`requiere_revision_humana` is always True; the result is advisory only.

Configuration via environment variables (all optional — sane defaults apply):
  INGRESO_MINIMO_HARD   Absolute income floor in ARS.  Default: 300_000
  INGRESO_MINIMO_SOFT   Preferred income floor in ARS.  Default: 600_000
  TASA_CUOTA_MENSUAL    Monthly instalment factor (cuota = precio x factor).
                        Default: 0.0065  (UVA 20-year reference rate)
  RATIO_CUOTA_MAX       Max allowed cuota/net-income ratio.  Default: 0.30

These values are intentionally NOT exposed in the API response or the UI.
"""

import os
import re

# ---------------------------------------------------------------------------
#  Configuration — income thresholds + mortgage eligibility (read once)
# ---------------------------------------------------------------------------

_INGRESO_MINIMO_HARD: float = float(os.getenv("INGRESO_MINIMO_HARD", 300_000))
_INGRESO_MINIMO_SOFT: float = float(os.getenv("INGRESO_MINIMO_SOFT", 600_000))
_TASA_CUOTA_MENSUAL: float  = float(os.getenv("TASA_CUOTA_MENSUAL",  0.0030))
_RATIO_CUOTA_MAX: float     = float(os.getenv("RATIO_CUOTA_MAX",     0.35))


# ---------------------------------------------------------------------------
#  Public entry point
# ---------------------------------------------------------------------------

def build_recommendation(entities: dict) -> dict:
    """
    Build a recommendation block from a normalised extraction result dict.

    Args:
        entities: The dict already post-processed by _post_process().

    Returns:
        A dict matching the Recomendacion schema.
    """
    sol  = entities.get("solicitante", {})
    emp  = entities.get("empleo", {})
    val  = entities.get("validaciones", {})
    meta = entities.get("metadatos", {})

    condiciones: list[str] = []   # factual observations (neutral)
    razones_hard: list[str] = []  # hard blockers → RECHAZAR
    razones_soft: list[str] = []  # soft concerns  → REVISAR

    docs = meta.get("documentos_procesados", [])

    # ------------------------------------------------------------------
    # 1. Document presence checks
    # ------------------------------------------------------------------
    recibo_docs = [d for d in docs if d.startswith("recibo_")]
    if not recibo_docs:
        razones_hard.append(
            "Recibo de sueldo no proporcionado: no es posible evaluar capacidad de pago."
        )
    else:
        n = len(recibo_docs)
        condiciones.append(
            f"{n} recibo{'s' if n > 1 else ''} de sueldo presente{'s' if n > 1 else ''}."
        )

    if "dni" not in docs:
        razones_soft.append(
            "DNI no proporcionado: la identidad del solicitante no puede verificarse."
        )
    else:
        condiciones.append("DNI presente.")

    # ------------------------------------------------------------------
    # 2. Identity validation
    # ------------------------------------------------------------------
    nombres_coinciden = val.get("nombres_coinciden", "")
    if nombres_coinciden == "ALERTA":
        razones_hard.append(
            "Los nombres del DNI y del recibo no coinciden: revisar identidad antes de continuar."
        )
    elif nombres_coinciden == "NO VERIFICABLE":
        if "dni" in docs and "recibo_sueldo" in docs:
            # Both docs present but name unreadable — soft concern
            razones_soft.append(
                "La coincidencia de nombres no pudo verificarse aunque ambos documentos están presentes."
            )
        # If one doc is missing it's already covered above
    elif nombres_coinciden == "OK":
        condiciones.append("Identidad verificada: nombres coinciden entre DNI y recibo.")

    # ------------------------------------------------------------------
    # 3. Payslip freshness
    # ------------------------------------------------------------------
    recibo_vigente = val.get("recibo_vigente", "")
    if recibo_vigente.startswith("ALERTA"):
        razones_hard.append(
            f"Recibo de sueldo vencido ({recibo_vigente.replace('ALERTA: ', '')}): "
            "el banco requiere un recibo de los últimos 3 meses."
        )
    elif recibo_vigente == "OK":
        condiciones.append("Recibo de sueldo vigente (dentro del período aceptado).")
    elif recibo_vigente == "NO VERIFICABLE" and "recibo_sueldo" in docs:
        razones_soft.append(
            "No se pudo determinar la fecha del recibo: verificar vigencia manualmente."
        )

    # ------------------------------------------------------------------
    # 4. Income evaluation — uses promedio when multi-recibo is available
    # ------------------------------------------------------------------
    historico = entities.get("haberes_historico") or {}
    promedio_val = historico.get("promedio_neto_pesos") if isinstance(historico, dict) else None

    neto_raw = emp.get("sueldo_neto", "")
    neto_val = _parse_amount(neto_raw)

    # Prefer promedio over single-period neto when available
    income_val   = promedio_val if promedio_val is not None else neto_val
    income_label = "promedio neto (3 meses)" if promedio_val is not None else "sueldo neto declarado"

    if income_val is not None:
        condiciones.append(
            f"Ingreso de referencia — {income_label}: {_fmt_ars(income_val)}."
        )
        if income_val < _INGRESO_MINIMO_HARD:
            razones_hard.append(
                "El ingreso neto de referencia no alcanza el mínimo requerido para acceder al crédito."
            )
        elif income_val < _INGRESO_MINIMO_SOFT:
            razones_soft.append(
                "El ingreso neto de referencia está por debajo del umbral preferido: "
                "evaluar capacidad de pago en función del monto solicitado."
            )
    elif recibo_docs:
        razones_soft.append(
            "No se pudo extraer el sueldo neto del recibo: verificar el monto manualmente."
        )

    # ------------------------------------------------------------------
    # 4b. Multi-recibo: tendencia and consistencia
    # ------------------------------------------------------------------
    if isinstance(historico, dict) and historico.get("periodos"):
        tendencia    = historico.get("tendencia", "")
        consistencia = historico.get("consistencia", "")
        n_periodos   = len(historico.get("periodos", []))

        if tendencia == "creciente":
            condiciones.append(
                f"Tendencia salarial: creciente en los últimos {n_periodos} meses — favorable."
            )
        elif tendencia == "estable":
            condiciones.append(
                f"Tendencia salarial: estable en los últimos {n_periodos} meses."
            )
        elif tendencia == "decreciente":
            condiciones.append(
                f"Tendencia salarial: decreciente en los últimos {n_periodos} meses."
            )
            razones_soft.append(
                "El sueldo neto muestra una tendencia decreciente en los últimos meses: "
                "evaluar estabilidad laboral antes de aprobar."
            )

        if consistencia == "ALERTA":
            razones_soft.append(
                "Se detectaron diferentes empleadores en los recibos provistos: "
                "verificar continuidad y estabilidad laboral."
            )
        elif consistencia == "OK" and n_periodos > 1:
            condiciones.append("Empleador consistente en todos los recibos provistos.")

    # ------------------------------------------------------------------
    # 4c. Mortgage eligibility — cuota vs. propiedad asignada
    #     Uses income_val (promedio or single neto) for the ratio check.
    #     persona_profile is injected by the personas workflow when the
    #     analysis is triggered from a mock persona.  For uploaded docs
    #     there is no assigned property so this check is skipped.
    # ------------------------------------------------------------------
    propiedad = entities.get("persona_profile", {}).get("propiedad") or {}
    precio_prop = propiedad.get("precio_pesos")

    if precio_prop and income_val is not None and income_val > 0:
        cuota_est = precio_prop * _TASA_CUOTA_MENSUAL
        ratio_act = cuota_est / income_val
        elegible  = propiedad.get("elegible", True)   # already computed in mock_data
        pct_str   = f"{ratio_act * 100:.1f}%"
        max_pct   = f"{_RATIO_CUOTA_MAX * 100:.0f}%"

        condiciones.append(
            f"Propiedad asignada: {propiedad.get('id', '?')} — "
            f"{propiedad.get('tipo', '')} en {propiedad.get('localidad', '')} — "
            f"{_fmt_ars(precio_prop)}."
        )
        condiciones.append(
            f"Cuota hipotecaria estimada: {_fmt_ars(cuota_est)} "
            f"({pct_str} del sueldo neto — límite: {max_pct})."
        )

        if not elegible:
            razones_hard.append(
                f"La cuota estimada para la propiedad asignada ({_fmt_ars(cuota_est)}) "
                f"representa el {pct_str} del sueldo neto, superando el límite del {max_pct}. "
                "El solicitante no puede afrontar esta propiedad con su ingreso actual."
            )
        elif ratio_act > _RATIO_CUOTA_MAX * 0.85:
            # Cuota is within the limit but close to it (>85% of the cap) → soft warning
            razones_soft.append(
                f"La cuota estimada ({_fmt_ars(cuota_est)}) representa el {pct_str} del sueldo neto, "
                f"cerca del límite del {max_pct}. Evaluar con margen ante posibles aumentos de cuota UVA."
            )

    # ------------------------------------------------------------------
    # 5. Critical field completeness (only when the relevant doc is present)
    # ------------------------------------------------------------------
    if recibo_docs:
        if not emp.get("empleador", "").strip():
            razones_soft.append("Empleador no identificado en el recibo.")
        if not emp.get("fecha_recibo", "").strip():
            razones_soft.append("Fecha del recibo no identificada.")

    if "dni" in docs:
        if not sol.get("nombre_completo", "").strip():
            razones_soft.append("Nombre completo no extraído del DNI.")

    # ------------------------------------------------------------------
    # 6. Aggregate employment type as an observation (no judgement)
    # ------------------------------------------------------------------
    tipo_empleo = emp.get("tipo_empleo", "")
    if tipo_empleo:
        condiciones.append(f"Tipo de empleo: {tipo_empleo}.")

    # ------------------------------------------------------------------
    # 7. Compute final decision
    # ------------------------------------------------------------------
    if razones_hard:
        estado    = "ROJO"
        decision  = "RECHAZAR"
        resumen   = (
            "La solicitud presenta condiciones que impiden su aprobación. "
            "Se recomienda rechazar o solicitar documentación adicional."
        )
        razones   = razones_hard + razones_soft
    elif razones_soft:
        estado    = "AMARILLO"
        decision  = "REVISAR"
        resumen   = (
            "La solicitud no presenta bloqueadores críticos pero requiere revisión "
            "manual antes de emitir una decisión."
        )
        razones   = razones_soft
    else:
        estado    = "VERDE"
        decision  = "APROBAR"
        resumen   = (
            "La solicitud cumple los criterios de evaluación. "
            "Se sugiere aprobar sujeto a revisión humana final."
        )
        razones   = ["Todos los criterios de evaluación fueron satisfactorios."]

    return {
        "estado": estado,
        "decision": decision,
        "resumen": resumen,
        "razones": razones,
        "condiciones_observadas": condiciones,
        "requiere_revision_humana": True,   # never False — advisory only
    }


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _parse_amount(raw: str) -> float | None:
    """
    Parse an Argentine-formatted amount string like "$1250000,00" → 1250000.0.
    Handles:
      - Leading "$", "ARS", or "$ " prefixes
      - Dot-separated thousands:  "1.250.000,00"  (already cleaned by _post_process)
      - Comma decimal separator:  "1250000,00"
      - Plain integers:           "1250000"
    Returns None if the string cannot be parsed.
    """
    if not raw:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", str(raw))   # strip currency symbols/spaces
    if not cleaned:
        return None
    # Remove remaining thousand-separator dots (sequences like "1.250.000")
    cleaned = re.sub(r"\.(?=\d{3}(?:[,.]|$))", "", cleaned)
    # Replace Argentine decimal comma with dot
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _fmt_ars(amount: float) -> str:
    """Format a float as ARS with thousand separators, no decimals."""
    return f"$ {amount:,.0f}".replace(",", ".")
