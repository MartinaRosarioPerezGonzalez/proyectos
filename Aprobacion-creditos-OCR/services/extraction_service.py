"""
Extraction Service — DemoBank Loan Application Asset
Extracts structured entities from transcribed loan application documents
(DNI + hasta 3 recibos de sueldo) using GPT-OSS-120B on IBM watsonx.ai.

Two-step pipeline:
  1. Extract entities from each document independently
  2. Run cross-validation (identity match between DNI and payslip)

Multi-recibo support:
  - recibo_texts accepts a list of 1-3 payslip transcriptions ordered from
    oldest to most recent.
  - empleo always reflects the MOST RECENT payslip (recibo_texts[-1]).
  - haberes_historico contains the per-period breakdown + derived stats
    (promedio_neto_pesos, tendencia, consistencia) calculated deterministically.
"""

import json
import os
import re
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from services.transcription_service import get_iam_token
from services.recommendation_service import build_recommendation
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

MODEL_ID = "openai/gpt-oss-120b"
MAX_RECIBO_AGE_MONTHS = 3       # Recibos older than this trigger an alert


# ---------------------------------------------------------------------------
#  Main extraction entry point
# ---------------------------------------------------------------------------

def extract_loan_entities(
    dni_text: str,
    recibo_text: str = "",          # kept for backwards compatibility (single recibo)
    api_key: str = None,
    project_id: str = None,
    url: str = None,
    persona_profile: dict = None,
    recibo_texts: list = None,      # preferred: list of 1-3 recibo transcriptions
) -> dict:
    """
    Extract structured entities from a loan application.

    Args:
        dni_text:        Transcribed text of the applicant's DNI document.
        recibo_text:     (legacy) Transcribed text of a single payslip.
                         Ignored when recibo_texts is provided.
        api_key:         IBM Cloud API Key (falls back to WATSONX_API_KEY env var).
        project_id:      Watsonx.ai project ID.
        url:             Watsonx.ai base URL.
        persona_profile: Optional dict with persona context (renaper, bcra, afip, propiedad).
                         When provided, it is embedded in the result BEFORE build_recommendation
                         runs so the mortgage eligibility check has access to the assigned property.
        recibo_texts:    List of 1-3 payslip transcriptions, ordered from oldest to most recent.
                         When provided, recibo_text is ignored.

    Returns:
        dict matching LoanApplicationExtractionResult schema, with optional
        top-level "error" key if the LLM call failed.
    """
    api_key     = api_key     or os.getenv("WATSONX_API_KEY")
    project_id  = project_id  or os.getenv("WATSONX_PROJECT_ID")
    url         = url         or os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    # Normalise recibo input → always work with a list
    if recibo_texts is not None:
        # Caller passed the new-style list; filter out empty strings
        texts = [t for t in recibo_texts if t and t.strip()]
    elif recibo_text and recibo_text.strip():
        texts = [recibo_text]
    else:
        texts = []

    try:
        access_token = get_iam_token(api_key)
    except Exception as e:
        return {"error": f"Failed to get IAM token: {e}"}

    api_url = f"{url}/ml/v1/text/chat?version=2023-05-29"

    # Build document sections for the prompt
    dni_section = (
        f"--- TEXTO DEL DNI ---\n{dni_text.strip()}\n--- FIN DNI ---"
        if dni_text and dni_text.strip()
        else "--- DNI: NO PROPORCIONADO ---"
    )

    # Build recibo sections — label each one by index (oldest first)
    recibo_sections = []
    total_recibos = len(texts)
    for idx, t in enumerate(texts):
        label_num  = idx + 1          # 1, 2, 3
        recibo_sections.append(
            f"--- RECIBO {label_num} DE {total_recibos} "
            f"({'MÁS ANTIGUO' if idx == 0 and total_recibos > 1 else 'MÁS RECIENTE' if idx == total_recibos - 1 and total_recibos > 1 else f'PERÍODO {label_num}'}) ---\n"
            f"{t.strip()}\n"
            f"--- FIN RECIBO {label_num} ---"
        )
    if not recibo_sections:
        recibo_sections = ["--- RECIBO DE SUELDO: NO PROPORCIONADO ---"]

    recibo_block = "\n\n".join(recibo_sections)

    today_str = date.today().strftime("%d/%m/%Y")
    today_iso = date.today().isoformat()

    # Build the SECCIÓN 2b block (only shown when multiple recibos provided)
    if total_recibos > 1:
        seccion_2b = f"""
---

SECCIÓN 2b — HISTORIAL DE HABERES (completar cuando hay MÁS DE UN recibo)

Se te proporcionaron {total_recibos} recibos. Para cada uno, extraé:
- **periodo**: mes/año del recibo en formato MM/YYYY
- **sueldo_bruto**: monto bruto (mismo formato que sueldo_bruto en SECCIÓN 2)
- **sueldo_neto**: monto neto (mismo formato que sueldo_neto en SECCIÓN 2)
- **empleador**: nombre del empleador en ese recibo

Completá el array "haberes_historico.periodos" con un objeto por cada recibo, en orden cronológico (más antiguo primero).
Los campos "empleo" (SECCIÓN 2) deben reflejar ÚNICAMENTE el recibo más reciente (RECIBO {total_recibos} DE {total_recibos}).
"""
    else:
        seccion_2b = ""

    # Build historial JSON template (only when multiple recibos)
    if total_recibos > 1:
        periodos_template = ",\n    ".join([
            '{"periodo": "", "sueldo_bruto": "", "sueldo_neto": "", "empleador": "", "alertas": []}'
            for _ in texts
        ])
        historico_json = f"""  "haberes_historico": {{{{
    "periodos": [
    {periodos_template}
    ],
    "promedio_neto_pesos": null,
    "tendencia": "",
    "consistencia": ""
  }}}},"""
    else:
        historico_json = '  "haberes_historico": null,'

    system_prompt = f"""Sos un analista bancario experto en evaluación de solicitudes de préstamos personales en Argentina.
Tu tarea es extraer entidades de documentos de un solicitante de préstamo (DNI y/o recibos de sueldo) y devolver un JSON válido.

La fecha de hoy es: {today_str}

---

SECCIÓN 1 — DATOS DEL SOLICITANTE (extraer del DNI)

1. **nombre_completo**:
   - Transcribí el nombre tal como aparece en el DNI argentino (generalmente en mayúsculas).
   - Formato estándar del DNI nuevo: "APELLIDO NOMBRE" o "APELLIDO, NOMBRE".
   - Si el DNI tiene frente y dorso, el nombre está en el FRENTE.
   - NO incluyas el número de trámite ni el número de DNI en este campo.

2. **dni** (número de documento):
   - Solo los dígitos, sin puntos ni espacios. Ej: "00000001".
   - Longitud esperada: 7 u 8 dígitos.
   - En el DNI aparece como "DNI 00.000.001" o simplemente como el número grande impreso.
   - NUNCA confundas el número de trámite (14 dígitos) con el número de DNI (7-8 dígitos).

3. **fecha_nacimiento**:
   - Formato: DD/MM/YYYY. Ej: "15/03/1985".
   - En el DNI aparece como "FECHA DE NACIMIENTO" o "NACIMIENTO".
   - Si está en formato YYYY-MM-DD (como en algunos DNI nuevos), convertila a DD/MM/YYYY.

4. **domicilio**:
   - Dirección completa tal como aparece en el DNI: calle, número, piso/dpto (si hay), localidad, provincia.
   - Ej: "AV. RIVADAVIA 1234 PISO 3 DPTO A - CABA".
   - Si no aparece (solo en el dorso que no fue proporcionado), dejá vacío ("").

---

SECCIÓN 2 — DATOS DEL EMPLEO (extraer del recibo MÁS RECIENTE)

Si se proporcionaron múltiples recibos, estos campos corresponden al ÚLTIMO recibo (el más reciente).

5. **empleador**:
   - Razón social o nombre del empleador tal como figura en el encabezado del recibo.
   - Puede ser una empresa privada, organismo público, municipalidad, etc.
   - Ej: "EMPRESA XYZ S.A.", "MINISTERIO DE EDUCACIÓN NACIÓN", "MUNICIPALIDAD DE ROSARIO".

6. **cuil**:
   - Formato: XX-XXXXXXXX-X (con guiones) o sin guiones. Conservá el formato que aparece.
   - El CUIL del EMPLEADO (solicitante), no el del empleador (CUIT).
   - Suele aparecer como "CUIL:", "C.U.I.L.:" en el encabezado del recibo.
   - Si no está explícito pero hay un DNI de 8 dígitos en el encabezado, el CUIL se puede inferir pero NO lo inventes — dejá vacío.

7. **sueldo_bruto**:
   - Importe total bruto del recibo MÁS RECIENTE, antes de deducciones.
   - Incluí el símbolo de moneda si aparece: "$", "ARS", etc.
   - Ej: "$ 850.000,00" o "850000.00".
   - En recibos argentinos suele llamarse "TOTAL REMUNERATIVO", "TOTAL BRUTO" o "HABERES".

8. **sueldo_neto**:
   - Importe que efectivamente percibe el empleado (lo que se deposita) del recibo MÁS RECIENTE.
   - Suele llamarse "NETO A COBRAR", "TOTAL NETO", "IMPORTE A PAGAR", "NETO A PAGAR".
   - Este es el campo más importante para el análisis crediticio.

9. **fecha_recibo**:
   - Mes y año del recibo MÁS RECIENTE. Formato: MM/YYYY. Ej: "09/2025".
   - Puede aparecer como "Período: 09/2025", "MES: SEPTIEMBRE 2025", etc.
   - Si aparece una fecha completa (con día), extraé solo mes y año: "01/09/2025" → "09/2025".

10. **antiguedad_laboral**:
    - Tiempo que lleva el empleado en esa empresa.
    - Puede aparecer como "ANTIGÜEDAD", "FECHA DE INGRESO" o calculada en años/meses.
    - Si aparece la fecha de ingreso (ej: "INGRESO: 15/03/2018"), calculá la antigüedad desde esa fecha hasta hoy ({today_str}).
    - Formato preferido: "X años Y meses" o "Z meses". Ej: "7 años 3 meses", "8 meses".
    - Si no aparece ni fecha de ingreso ni antigüedad explícita, dejá vacío ("").

11. **tipo_empleo**:
    - Clasificá el empleo en una de estas categorías:
      * "Empleado privado" — empresa privada (SA, SRL, etc.)
      * "Empleado público" — Estado nacional, provincial o municipal
      * "Monotributista" — si el recibo indica facturación en lugar de haberes
      * "Otro" — cualquier otro caso
{seccion_2b}
---

SECCIÓN 3 — VALIDACIÓN DE IDENTIDAD (cruzar DNI vs recibo de sueldo más reciente)

12. **nombres_coinciden**:
    - Comparar el nombre del DNI con el nombre que figura en el recibo de sueldo más reciente (suele estar en el encabezado como "APELLIDO Y NOMBRES:", "EMPLEADO:", etc.).
    - Valores posibles:
      * "OK" — los nombres coinciden (pueden tener pequeñas diferencias de formato: mayúsculas vs minúsculas, orden apellido/nombre, etc.)
      * "ALERTA" — los nombres son claramente diferentes
      * "NO VERIFICABLE" — uno de los dos documentos no fue proporcionado o el nombre no es legible

13. **detalle_coincidencia**:
    - Breve explicación de la comparación. Ej:
      * "DNI: PERSONA UNO | Recibo: UNO PERSONA — Coinciden (diferente orden)"
      * "DNI: PERSONA DOS | Recibo: PERSONA TRES — No coinciden, posible error"
      * "Recibo no proporcionado, no se puede verificar"

14. **recibo_vigente**:
    - Evaluá si el recibo MÁS RECIENTE está vigente (no más de {MAX_RECIBO_AGE_MONTHS} meses de antigüedad desde la fecha de hoy: {today_str}).
    - Valores posibles:
      * "OK" — el recibo es del período esperado (últimos {MAX_RECIBO_AGE_MONTHS} meses)
      * "ALERTA: recibo con X meses de antigüedad" — si es más viejo
      * "NO VERIFICABLE" — si no se pudo extraer la fecha del recibo

---

REGLAS GENERALES CRÍTICAS:

- NÚMEROS: Remové siempre los puntos de miles de los montos: "$1.250.000,00" → "$1250000,00".
- DNI: 7-8 dígitos sin puntos. Número de TRÁMITE ≠ número de DNI (el trámite tiene 14 dígitos).
- CUIL: incluir con o sin guiones según como aparece.
- FECHAS: Siempre en formato DD/MM/YYYY para nacimiento, MM/YYYY para recibo.
- CAMPOS VACÍOS: Si un campo no aparece en el documento, dejá exactamente "" (string vacío), NUNCA null ni "No disponible".
- ALERTAS: Agregá una alerta descriptiva en el array correspondiente cada vez que:
  * Un campo no pudo ser leído con certeza (valor poco legible o ambiguo)
  * Hay inconsistencia entre documentos
  * Un campo crítico está ausente (DNI, nombre, sueldo neto)
  * El recibo tiene más de {MAX_RECIBO_AGE_MONTHS} meses de antigüedad
- DOCUMENTOS FALTANTES: Si uno de los dos documentos no fue proporcionado, completá los campos de esa sección con "" y agregá una alerta general: "Documento X no proporcionado".
- NO INVENTAR: Nunca completés un campo con un valor que no esté explícitamente en el documento. Antes preferí dejarlo vacío con una alerta.

---

EJEMPLOS DE REFERENCIA:

EJEMPLO 1 (DNI + recibo de empleado privado):
  DNI → nombre: "PERSONA UNO", dni: "00000001", nacimiento: "15/03/1985", domicilio: "CALLE DEMO 100 CIUDAD DEMO"
  Recibo → empleador: "EMPRESA DEMO SA", cuil: "20-00000001-4", bruto: "$850000", neto: "$680000", fecha: "09/2025", antigüedad: "3 años 2 meses", tipo: "Empleado privado"
  Validación → nombres_coinciden: "OK", detalle: "DNI: PERSONA UNO | Recibo: PERSONA UNO — Coinciden", vigente: "OK"

EJEMPLO 2 (recibo de empleado público, recibo viejo):
  Recibo → empleador: "ORGANISMO PÚBLICO DEMO", tipo: "Empleado público", fecha: "05/2025"
  Validación → recibo_vigente: "ALERTA: recibo con 4 meses de antigüedad"

EJEMPLO 3 (nombres no coinciden):
  DNI → nombre: "PERSONA DOS"
  Recibo → nombre empleado: "PERSONA TRES"
  Validación → nombres_coinciden: "ALERTA", detalle: "DNI: PERSONA DOS | Recibo: PERSONA TRES — No coinciden, revisar identidad"

---

JSON A COMPLETAR:
{{{{
  "solicitante": {{{{
    "nombre_completo": "",
    "dni": "",
    "fecha_nacimiento": "",
    "domicilio": "",
    "alertas_solicitante": []
  }}}},
  "empleo": {{{{
    "empleador": "",
    "cuil": "",
    "sueldo_bruto": "",
    "sueldo_neto": "",
    "fecha_recibo": "",
    "antiguedad_laboral": "",
    "tipo_empleo": "",
    "alertas_empleo": []
  }}}},
  {historico_json}
  "validaciones": {{{{
    "nombres_coinciden": "",
    "detalle_coincidencia": "",
    "recibo_vigente": "",
    "alertas_validacion": []
  }}}},
  "metadatos": {{{{
    "documentos_procesados": [],
    "metodo_extraccion": "",
    "alertas_generales": []
  }}}}
}}}}"""

    combined_text = f"{dni_section}\n\n{recibo_block}"

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Extraé las entidades de los siguientes documentos del solicitante "
                    "y devolvé ÚNICAMENTE el JSON válido, sin texto adicional:\n\n"
                    f"{combined_text}"
                ),
            },
        ],
        "project_id": project_id,
        "model_id": MODEL_ID,
        "decoding_method": "greedy",
        "max_tokens": 3000,
        "min_tokens": 1,
        "temperature": 0.1,
        "repetition_penalty": 1.1,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    print(f"  Calling Watsonx Model {MODEL_ID} for loan entity extraction ({total_recibos} recibo(s))...")
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=180)
        if response.status_code != 200:
            return {"error": f"Watsonx API error: {response.status_code} — {response.text}"}

        # GPT-OSS-120B is a reasoning model: the final answer lands in "content"
        # while the chain-of-thought lives in "reasoning_content". Both can be
        # present; we want "content". Fall back to "reasoning_content" only when
        # "content" is absent (should not normally happen with enough max_tokens).
        message = response.json()["choices"][0]["message"]
        generated_response = message.get("content") or message.get("reasoning_content", "")
        if not generated_response:
            return {"error": "Model returned an empty response", "raw_message": message}

    except requests.exceptions.Timeout:
        return {"error": "Watsonx API timed out after 180 seconds."}
    except Exception as e:
        return {"error": f"Request failed: {e}"}

    # --- Parse JSON from LLM response ---
    try:
        start = generated_response.find("{")
        end   = generated_response.rfind("}") + 1
        if start != -1 and end > start:
            parsed = json.loads(generated_response[start:end])
        else:
            return {"error": "No JSON found in model response", "raw": generated_response}
    except Exception as e:
        return {"error": f"Failed to parse JSON: {e}", "raw": generated_response}

    # --- Post-processing ---
    # Inject persona_profile before _post_process so that build_recommendation
    # has access to the assigned property for the mortgage eligibility check.
    if persona_profile is not None:
        parsed["persona_profile"] = persona_profile
    parsed = _post_process(parsed, dni_text, texts)
    return parsed


# ---------------------------------------------------------------------------
#  Post-processing: deterministic corrections after LLM extraction
# ---------------------------------------------------------------------------

def _post_process(entities: dict, dni_text: str, recibo_texts: list) -> dict:
    """
    Apply rule-based corrections on top of the LLM output.
    Never trusts the LLM blindly for fields that can be verified deterministically.

    recibo_texts: list of transcribed payslip strings (oldest first).
    """
    # Ensure all top-level keys exist
    entities.setdefault("solicitante", {})
    entities.setdefault("empleo", {})
    entities.setdefault("validaciones", {})
    entities.setdefault("metadatos", {})

    sol  = entities["solicitante"]
    emp  = entities["empleo"]
    val  = entities["validaciones"]
    meta = entities["metadatos"]

    # 1. Clean DNI — remove dots, spaces, dashes
    dni = sol.get("dni", "")
    if dni:
        cleaned_dni = re.sub(r"[.\s\-]", "", str(dni))
        sol["dni"] = cleaned_dni
        if len(cleaned_dni) not in (7, 8):
            sol.setdefault("alertas_solicitante", []).append(
                f"DNI con longitud inesperada ({len(cleaned_dni)} dígitos): '{cleaned_dni}'. "
                "Verificar manualmente."
            )

    # 2. Clean sueldo fields — remove thousand-separator dots for consistency
    #    Apply to both empleo (most recent) and each period in haberes_historico
    for field in ("sueldo_bruto", "sueldo_neto"):
        raw = emp.get(field, "")
        if raw:
            emp[field] = re.sub(r"(?<=\d)\.(?=\d{3})", "", str(raw))

    # 3. Compute haberes_historico deterministically from LLM output
    historico_raw = entities.get("haberes_historico") or {}
    periodos_raw  = historico_raw.get("periodos", []) if isinstance(historico_raw, dict) else []

    if periodos_raw and len(periodos_raw) >= 1:
        # Clean amounts in each period
        cleaned_periodos = []
        neto_values = []
        empleadores = set()

        for p in periodos_raw:
            if not isinstance(p, dict):
                continue
            periodo_obj = {
                "periodo":      p.get("periodo", ""),
                "sueldo_bruto": re.sub(r"(?<=\d)\.(?=\d{3})", "", str(p.get("sueldo_bruto", ""))),
                "sueldo_neto":  re.sub(r"(?<=\d)\.(?=\d{3})", "", str(p.get("sueldo_neto", ""))),
                "empleador":    p.get("empleador", ""),
                "alertas":      p.get("alertas", []),
            }
            cleaned_periodos.append(periodo_obj)

            # Parse neto for stats
            neto_val = _parse_amount_simple(periodo_obj["sueldo_neto"])
            if neto_val is not None:
                neto_values.append(neto_val)
            if periodo_obj["empleador"].strip():
                empleadores.add(periodo_obj["empleador"].strip())

        # Calculate promedio, tendencia, consistencia
        promedio = sum(neto_values) / len(neto_values) if neto_values else None

        tendencia = ""
        if len(neto_values) >= 2:
            first, last = neto_values[0], neto_values[-1]
            delta_pct = (last - first) / first if first > 0 else 0
            if delta_pct > 0.03:          # > 3% growth
                tendencia = "creciente"
            elif delta_pct < -0.03:       # > 3% decline
                tendencia = "decreciente"
            else:
                tendencia = "estable"

        consistencia = "OK"
        if len(empleadores) > 1:
            consistencia = "ALERTA"

        entities["haberes_historico"] = {
            "periodos":           cleaned_periodos,
            "promedio_neto_pesos": promedio,
            "tendencia":          tendencia,
            "consistencia":       consistencia,
        }

        # Sync empleo (most recent period) if empleo fields are empty
        if cleaned_periodos:
            most_recent = cleaned_periodos[-1]
            if not emp.get("sueldo_neto") and most_recent.get("sueldo_neto"):
                emp["sueldo_neto"]  = most_recent["sueldo_neto"]
                emp["sueldo_bruto"] = most_recent.get("sueldo_bruto", "")
            if not emp.get("empleador") and most_recent.get("empleador"):
                emp["empleador"] = most_recent["empleador"]
            if not emp.get("fecha_recibo") and most_recent.get("periodo"):
                emp["fecha_recibo"] = most_recent["periodo"]
    else:
        # No multi-recibo data — ensure key is present as None
        entities["haberes_historico"] = None

    # 4. Validate recibo date freshness (deterministic override of LLM's opinion)
    fecha_recibo = emp.get("fecha_recibo", "")
    if fecha_recibo:
        recibo_date = _parse_periodo(fecha_recibo)
        if recibo_date:
            months_old = (
                (date.today().year - recibo_date.year) * 12
                + (date.today().month - recibo_date.month)
            )
            if months_old > MAX_RECIBO_AGE_MONTHS:
                val["recibo_vigente"] = f"ALERTA: recibo con {months_old} meses de antigüedad"
                val.setdefault("alertas_validacion", []).append(
                    f"El recibo de sueldo tiene {months_old} meses de antigüedad "
                    f"(período {fecha_recibo}). El banco acepta hasta {MAX_RECIBO_AGE_MONTHS} meses."
                )
            else:
                val["recibo_vigente"] = "OK"

    # 5. Track which documents were provided
    docs = []
    if dni_text and dni_text.strip():
        docs.append("dni")
    for i, t in enumerate(recibo_texts):
        if t and t.strip():
            docs.append(f"recibo_{i + 1}")
    meta["documentos_procesados"] = docs

    # 6. Alert if critical documents are missing
    if "dni" not in docs:
        meta.setdefault("alertas_generales", []).append(
            "DNI no proporcionado — no se pueden verificar datos de identidad."
        )
    if not any(d.startswith("recibo_") for d in docs):
        meta.setdefault("alertas_generales", []).append(
            "Recibo de sueldo no proporcionado — no se puede evaluar capacidad de pago."
        )

    # 7. Build recommendation block (deterministic, uses post-processed data)
    entities["recomendacion"] = build_recommendation(entities)

    return entities


def _parse_amount_simple(raw: str):
    """
    Parse an Argentine-formatted amount string → float or None.
    Handles "$1250000,00", "1.250.000,00" (already cleaned by step 2).
    """
    if not raw:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", str(raw))
    if not cleaned:
        return None
    # Remove remaining thousand-separator dots
    cleaned = re.sub(r"\.(?=\d{3}(?:[,.]|$))", "", cleaned)
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_periodo(periodo_str: str):
    """
    Try to parse a period string like "09/2025" or "9/2025" into a date object
    set to the first day of that month. Returns None on failure.
    """
    if not periodo_str:
        return None
    # Match MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{4})$", periodo_str.strip())
    if m:
        try:
            return date(int(m.group(2)), int(m.group(1)), 1)
        except ValueError:
            return None
    # Match DD/MM/YYYY — take month/year only
    m2 = re.match(r"^\d{1,2}/(\d{1,2})/(\d{4})$", periodo_str.strip())
    if m2:
        try:
            return date(int(m2.group(2)), int(m2.group(1)), 1)
        except ValueError:
            return None
    return None
