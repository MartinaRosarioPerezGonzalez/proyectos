"""
Payslip Generator — DemoBank Loan Application Asset
Generates a mock plain-text payslip (recibo de sueldo) for a persona dict
in the same layout as the real sample PDF.  The resulting text is fed
directly to extract_loan_entities() via the extract-from-text endpoint.
"""

from datetime import date

# ---------------------------------------------------------------------------
#  Salary table by AFIP category
#  (bruto, neto) — realistic ARS figures for mid-2026
# ---------------------------------------------------------------------------
_SALARY_TABLE = {
    "relacion_dependencia": {
        "default":   (1_820_000, 1_092_000),
        # employer-specific overrides
        "Empresa Demo S.A.":       (1_950_000, 1_170_000),
        "Empresa Demo S.R.L.":     (  980_000,   588_000),   # deliberately low → REVISAR
        "Organismo Público Demo":  (2_100_000, 1_260_000),
    },
    "monotributista": {
        "default": (1_350_000, 1_080_000),
    },
    "autonomo": {
        "default": (1_600_000, 1_200_000),
    },
}

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _fmt(amount: int) -> str:
    """Format integer as Argentine 'X.XXX.XXX,00'."""
    return f"{amount:,.0f}".replace(",", ".") + ",00"


def _employer_label(afip: dict) -> str:
    cat = afip.get("categoria", "")
    if cat == "relacion_dependencia":
        return afip.get("empleador", "Empleador S.A.")
    if cat == "monotributista":
        grade = afip.get("categoria_monotributo", "")
        return f"Monotributista Categoría {grade}" if grade else "Monotributista"
    if cat == "autonomo":
        return afip.get("actividad", "Actividad autónoma")
    return "Empleador"


def _tipo_empleo_label(afip: dict) -> str:
    cat = afip.get("categoria", "")
    mapping = {
        "relacion_dependencia": "Empleado en relación de dependencia",
        "monotributista":       "Monotributista",
        "autonomo":             "Autónomo",
    }
    return mapping.get(cat, "Otro")


def _salaries(afip: dict) -> tuple[int, int]:
    cat = afip.get("categoria", "relacion_dependencia")
    table = _SALARY_TABLE.get(cat, _SALARY_TABLE["relacion_dependencia"])
    employer = afip.get("empleador", "")
    return table.get(employer, table["default"])


def _cuit_empleador(afip: dict) -> str:
    """Return a plausible mock CUIT for the employer."""
    cuil_map = {
        "Empresa Demo S.A.":      "30-00000001-8",
        "Empresa Demo S.R.L.":    "30-00000002-9",
        "Organismo Público Demo": "30-00000003-2",
    }
    return cuil_map.get(afip.get("empleador", ""), "30-99999999-9")


def _antiguedad_label(fecha_ingreso_str: str) -> str:
    """Return 'X años Y meses' from an ISO date string."""
    try:
        ingreso = date.fromisoformat(fecha_ingreso_str)
        today   = date.today()
        years   = today.year - ingreso.year
        months  = today.month - ingreso.month
        if months < 0:
            years -= 1
            months += 12
        if years > 0:
            return f"{years} años {months} meses" if months else f"{years} años"
        return f"{months} meses"
    except Exception:
        return "N/D"


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def generate_payslip_text(persona: dict, override_date: date = None, override_salaries: tuple = None) -> str:
    """
    Build a plain-text recibo de sueldo for the given persona dict
    (as returned by mock_data.get_persona_by_index).

    The layout mirrors the real sample payslip so the AI extraction
    system prompt examples align correctly.

    Args:
        persona:           Full persona dict.
        override_date:     Use this date instead of today (for multi-month generation).
        override_salaries: (bruto, neto) tuple to override the salary table lookup.
    """
    r    = persona["renaper"]
    afip = persona["afip"]

    employer   = _employer_label(afip)
    cuit_emp   = _cuit_empleador(afip)
    bruto, neto = override_salaries if override_salaries else _salaries(afip)
    ref_date   = override_date if override_date else date.today()
    _MESES_ES  = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    periodo    = f"{_MESES_ES[ref_date.month - 1]} {ref_date.year}"
    mes_anio   = ref_date.strftime("%m/%Y")
    fecha_pago = ref_date.strftime("%d.%m.%Y")
    antiguedad = _antiguedad_label(afip.get("fecha_inscripcion", ""))
    tipo_label = _tipo_empleo_label(afip)

    lines = [
        "",
        f"  {employer:<40}CUIT {cuit_emp}   Hoja 1",
        f"   Periodo liquidado :  {periodo}",
        f"   {r['nombre_completo']:<38}Nro.personal    {r['dni']}",
        f"  Fecha de ingreso  {afip.get('fecha_inscripcion','N/D')}",
        f"    Antigüedad     {antiguedad}",
        f"  CUIL    {r['cuil']}                   Sdo.Basico {_fmt(bruto)}",
        f"                                   Cat.: {tipo_label}",
        " ----------------Ultimo deposito de Cargas Sociales--------------",
        f"  Banco   Nacion                Fecha {fecha_pago}  Periodo {mes_anio}",
        "-"*66,
        " Concepto                             H A B E R E S    Retenciones",
        " Cod   Descripcion          Cant    Sin Aport. Con Aport",
        "-"*66,
        "",
        f" 4000 Pago p. mes curso              {_fmt(bruto)}",
        "",
        "",
        "",
        "",
        "",
        "",
        " De existir el rubro Adicional Empresa, el mismo absorbera",
        " en su totalidad cualquier incremento que sea otorgado de acuerdo",
        " al marco regulatorio aplicable.",
        "",
        "",
        "                           ---------     ----------     ---------",
        f"        TOTALES       {_fmt(bruto)}",
        "",
        "",
        f"                              Neto a pagar           {_fmt(neto)}",
        "",
        " Recibi conforme la suma de pesos: - - - - - - - - - - -",
        "",
        f"  Lugar de Pago  CABA                  Fecha de Pago   {fecha_pago}",
        " " + "-"*64,
        "",
        "",
        " Original                                         Firma Empleado",
    ]
    return "\n".join(lines)


def generate_payslip_texts_3months(persona: dict) -> list:
    """
    Generate 3 consecutive monthly payslips (mes-2, mes-1, mes actual) for a persona.

    Salary scaling simulates realistic ARS increases observed in the sample PDFs
    (Persona Uno: +15% mayo→junio, +15% junio→julio):
      mes-2 (oldest):  base × 0.76   (≈ two step-backs of ~15%)
      mes-1:           base × 0.87   (≈ one step-back of ~13%)
      mes actual:      base           (current salary — most recent)

    Returns a list of 3 payslip text strings ordered oldest → newest.
    The most recent one matches what generate_payslip_text() produces.
    """
    from dateutil.relativedelta import relativedelta

    today    = date.today()
    base_bruto, base_neto = _salaries(persona["afip"])

    months_back = [2, 1, 0]
    # Scaling factors (oldest → newest): simulates ~13-15% monthly increase
    scale_factors = [0.76, 0.87, 1.0]

    texts = []
    for months_ago, scale in zip(months_back, scale_factors):
        ref_date = today - relativedelta(months=months_ago)
        scaled_bruto = round(base_bruto * scale / 1000) * 1000  # round to thousands
        scaled_neto  = round(base_neto  * scale / 1000) * 1000
        text = generate_payslip_text(
            persona,
            override_date=(ref_date.replace(day=1)),
            override_salaries=(scaled_bruto, scaled_neto),
        )
        texts.append(text)

    return texts  # [oldest, middle, most_recent]


def generate_dni_text(persona: dict) -> str:
    """
    Build a short plain-text DNI block for the given persona dict.
    This lets the AI cross-validate identity (DNI name vs payslip name).
    """
    r = persona["renaper"]
    # Convert ISO date to DD/MM/YYYY
    try:
        d = date.fromisoformat(r["fecha_nacimiento"])
        nacimiento = d.strftime("%d/%m/%Y")
    except Exception:
        nacimiento = r["fecha_nacimiento"]

    lines = [
        "REPÚBLICA ARGENTINA",
        "DOCUMENTO NACIONAL DE IDENTIDAD",
        "",
        f"APELLIDO Y NOMBRES: {r['nombre_completo'].upper()}",
        f"DNI: {r['dni']}",
        f"FECHA DE NACIMIENTO: {nacimiento}",
        f"CUIL: {r['cuil']}",
        f"DOMICILIO: {r['domicilio'].upper()}",
        "",
        "ORIGINAL — VÁLIDO EN TODO EL TERRITORIO NACIONAL",
    ]
    return "\n".join(lines)
