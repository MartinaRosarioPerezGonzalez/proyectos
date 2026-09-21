"""
Mock Data — DemoBank Loan Application Asset
Provides static persona data for the personas workflow demo.
All recipients point to demo@example.com for demo purposes.

Property matching logic
-----------------------
assign_property() selects the best-fit property for a persona based on their
salary. The rule mirrors the standard mortgage eligibility criterion:

  cuota_estimada  = precio_propiedad x TASA_CUOTA_MENSUAL
  ratio_cuota     = cuota_estimada / sueldo_neto
  elegible        = ratio_cuota <= RATIO_CUOTA_MAX

TASA_CUOTA_MENSUAL  Approximate monthly instalment factor for a UVA 20-year
                    mortgage.  Default: 0.0065 (approx 6.5 per-mille of price).
RATIO_CUOTA_MAX     Maximum allowed cuota/neto ratio.  Default: 0.30 (30 %).

Both are configurable via env vars so the demo can be tweaked without code
changes.  When no property is affordable, the cheapest one is returned with
an `elegible` flag set to False so the UI and recommendation engine can warn.
"""

import os

# ---------------------------------------------------------------------------
#  Source data (as provided)
# ---------------------------------------------------------------------------

RENAPER = [
    {
        "dni": "00000001",
        "nombre_completo": "Persona Uno",
        "cuil": "20-00000001-4",
        "fecha_nacimiento": "1985-03-12",
        "domicilio": "Calle Demo 100, Ciudad Demo",
    },
    {
        "dni": "00000002",
        "nombre_completo": "Persona Dos",
        "cuil": "27-00000002-3",
        "fecha_nacimiento": "1992-07-28",
        "domicilio": "Calle Demo 200, Ciudad Demo",
    },
    {
        "dni": "00000003",
        "nombre_completo": "Persona Tres",
        "cuil": "20-00000003-6",
        "fecha_nacimiento": "1978-11-05",
        "domicilio": "Calle Demo 300, Ciudad Demo",
    },
    {
        "dni": "00000004",
        "nombre_completo": "Persona Cuatro",
        "cuil": "27-00000004-1",
        "fecha_nacimiento": "1998-02-14",
        "domicilio": "Calle Demo 400, Ciudad Demo",
    },
    {
        "dni": "00000005",
        "nombre_completo": "Persona Cinco",
        "cuil": "20-00000005-9",
        "fecha_nacimiento": "1988-09-30",
        "domicilio": "Calle Demo 500, Ciudad Demo",
    },
]

BCRA = [
    {
        "cuil": "20-00000001-4",
        "situacion": "1 - Normal",
        "score": 940,
        "deudas_activas_pesos": 0,
        "informes_negativos_12m": False,
    },
    {
        "cuil": "27-00000002-3",
        "situacion": "1 - Normal",
        "score": 910,
        "deudas_activas_pesos": 85000,
        "informes_negativos_12m": False,
    },
    {
        "cuil": "20-00000003-6",
        "situacion": "2 - Riesgo bajo",
        "score": 720,
        "deudas_activas_pesos": 340000,
        "informes_negativos_12m": True,
    },
    {
        "cuil": "27-00000004-1",
        "situacion": "1 - Normal",
        "score": 965,
        "deudas_activas_pesos": 0,
        "informes_negativos_12m": False,
    },
    {
        "cuil": "20-00000005-9",
        "situacion": "1 - Normal",
        "score": 955,
        "deudas_activas_pesos": 120000,
        "informes_negativos_12m": False,
    },
]

AFIP = [
    {
        "cuil": "20-00000001-4",
        "categoria": "relacion_dependencia",
        "empleador": "Empresa Demo S.A.",
        "estado": "activo",
        "fecha_inscripcion": "2010-04-01",
    },
    {
        "cuil": "27-00000002-3",
        "categoria": "monotributista",
        "categoria_monotributo": "H",
        "estado": "activo",
        "fecha_inscripcion": "2018-06-15",
    },
    {
        "cuil": "20-00000003-6",
        "categoria": "relacion_dependencia",
        "empleador": "Empresa Demo S.R.L.",
        "estado": "activo",
        "fecha_inscripcion": "2005-08-20",
    },
    {
        "cuil": "27-00000004-1",
        "categoria": "autonomo",
        "actividad": "Servicios de consultoría empresarial",
        "estado": "activo",
        "fecha_inscripcion": "2020-03-10",
    },
    {
        "cuil": "20-00000005-9",
        "categoria": "relacion_dependencia",
        "empleador": "Organismo Público Demo",
        "estado": "activo",
        "fecha_inscripcion": "2012-02-28",
    },
]

PROPIEDADES = [
    {"id": "HOG-001", "direccion": "Av. Corrientes 3840, Piso 5 Dto B", "localidad": "CABA",           "tipo": "Departamento", "superficie_m2": 30, "ambientes": 2, "precio_pesos": 65_000_000, "apta_hipoteca": True,  "estado_documental": "verificada"},
    {"id": "HOG-002", "direccion": "Gurruchaga 1456, PB A",              "localidad": "CABA",           "tipo": "PH",           "superficie_m2": 68, "ambientes": 3, "precio_pesos": 185_000_000, "apta_hipoteca": True,  "estado_documental": "verificada"},
    {"id": "HOG-003", "direccion": "San Lorenzo 892, Piso 2 Dto A",      "localidad": "Rosario",        "tipo": "Departamento", "superficie_m2": 48, "ambientes": 2, "precio_pesos":  98_000_000, "apta_hipoteca": True,  "estado_documental": "verificada"},
    {"id": "HOG-004", "direccion": "Colón 234, Piso 3 Dto B",            "localidad": "Córdoba Capital","tipo": "Departamento", "superficie_m2": 55, "ambientes": 2, "precio_pesos": 112_000_000, "apta_hipoteca": True,  "estado_documental": "verificada"},
    {"id": "HOG-005", "direccion": "Arístides Villanueva 540",           "localidad": "Mendoza Capital","tipo": "Casa",         "superficie_m2": 90, "ambientes": 3, "precio_pesos": 165_000_000, "apta_hipoteca": True,  "estado_documental": "verificada"},
]

# All demo emails go to the same address for testing
_DEMO_EMAIL = "demo@example.com"

_EMAILS = {
    "20-00000001-4": _DEMO_EMAIL,
    "27-00000002-3": _DEMO_EMAIL,
    "20-00000003-6": _DEMO_EMAIL,
    "27-00000004-1": _DEMO_EMAIL,
    "20-00000005-9": _DEMO_EMAIL,
}

# Indexed lookups (built once at import)
_BCRA_BY_CUIL  = {r["cuil"]: r for r in BCRA}
_AFIP_BY_CUIL  = {r["cuil"]: r for r in AFIP}

# ---------------------------------------------------------------------------
#  Property matching — mortgage eligibility rule
# ---------------------------------------------------------------------------

# Monthly instalment factor: cuota ≈ precio × factor
# 0.0030 corresponds to a 30-year UVA-subsidised mortgage (HomeLoan program).
_TASA_CUOTA_MENSUAL: float = float(os.getenv("TASA_CUOTA_MENSUAL", 0.0030))
# Maximum cuota-to-net-income ratio allowed (DemoBank HomeLoan: 35 %)
_RATIO_CUOTA_MAX: float    = float(os.getenv("RATIO_CUOTA_MAX", 0.35))


def assign_property(sueldo_neto_pesos: float) -> dict:
    """
    Return the most suitable property for a given monthly net income.

    Selection logic:
      1. Compute the estimated monthly instalment for each property.
      2. Keep only properties where cuota / sueldo_neto <= RATIO_CUOTA_MAX.
      3. From the eligible set, pick the most expensive one the applicant
         can afford (best possible property within their budget).
      4. If no property is affordable, fall back to the cheapest one and
         set `elegible=False` so downstream checks can raise an alert.

    The returned dict is a copy of the PROPIEDADES entry augmented with:
      - elegible (bool)
      - cuota_estimada (float)   monthly payment estimate in ARS
      - ratio_cuota   (float)    cuota / sueldo_neto ratio
    """
    best_eligible   = None
    cheapest        = None

    for prop in sorted(PROPIEDADES, key=lambda p: p["precio_pesos"]):
        cuota = prop["precio_pesos"] * _TASA_CUOTA_MENSUAL
        ratio = cuota / sueldo_neto_pesos if sueldo_neto_pesos > 0 else float("inf")

        # Track cheapest overall (fallback when nothing is affordable)
        if cheapest is None:
            cheapest = {**prop, "elegible": False, "cuota_estimada": cuota, "ratio_cuota": ratio}

        if ratio <= _RATIO_CUOTA_MAX:
            # Keep updating best_eligible — we iterate cheapest→most expensive,
            # so the last one that fits is the most expensive affordable property.
            best_eligible = {**prop, "elegible": True, "cuota_estimada": cuota, "ratio_cuota": ratio}

    return best_eligible if best_eligible is not None else cheapest

# ---------------------------------------------------------------------------
#  Public helpers
# ---------------------------------------------------------------------------

def get_personas_list() -> list[dict]:
    """Return a summary list suitable for the UI persona cards."""
    result = []
    for i, p in enumerate(RENAPER):
        bcra = _BCRA_BY_CUIL.get(p["cuil"], {})
        ciudad = p["domicilio"].split(",")[-1].strip()
        result.append({
            "id": i,
            "nombre_completo": p["nombre_completo"],
            "dni": p["dni"],
            "cuil": p["cuil"],
            "ciudad": ciudad,
            "situacion_bcra": bcra.get("situacion", "—"),
            "score_bcra": bcra.get("score", 0),
        })
    return result


def get_persona_by_index(i: int) -> dict:
    """Return the full merged persona dict for index i (0-based).

    The propiedad field is now assigned dynamically via assign_property()
    using the salary table from payslip_generator, so the best affordable
    property is selected for each persona based on their income.
    """
    if i < 0 or i >= len(RENAPER):
        raise IndexError(f"Persona index {i} out of range")
    p    = RENAPER[i]
    cuil = p["cuil"]

    # Resolve salary for this persona from the AFIP record + salary table
    # Import here to avoid circular imports (payslip_generator imports nothing
    # from mock_data).
    from services.payslip_generator import _salaries
    afip = _AFIP_BY_CUIL.get(cuil, {})
    _, neto = _salaries(afip)

    propiedad = PROPIEDADES[0] if cuil == "20-00000001-4" else assign_property(float(neto))

    return {
        "id": i,
        "email": _EMAILS.get(cuil, _DEMO_EMAIL),
        "renaper": p,
        "bcra":  _BCRA_BY_CUIL.get(cuil, {}),
        "afip":  afip,
        "propiedad": propiedad,
    }
