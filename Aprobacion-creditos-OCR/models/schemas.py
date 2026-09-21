# ------------------------------------------------------------------------------
#  Schemas — DemoBank Loan Application Asset
# ------------------------------------------------------------------------------

from typing import List, Literal, Optional
from pydantic import BaseModel

class Solicitante(BaseModel):
    nombre_completo: str = ""
    dni: str = ""
    fecha_nacimiento: str = ""          # DD/MM/YYYY
    domicilio: str = ""
    alertas_solicitante: List[str] = []


class Empleo(BaseModel):
    empleador: str = ""                 # Nombre/razón social del empleador
    cuil: str = ""                      # CUIL del solicitante (XX-XXXXXXXX-X)
    sueldo_bruto: str = ""              # Monto bruto del período más reciente
    sueldo_neto: str = ""               # Monto neto del período más reciente
    fecha_recibo: str = ""              # Mes/año del recibo más reciente — MM/YYYY
    antiguedad_laboral: str = ""        # Ej: "3 años 2 meses", "6 meses"
    tipo_empleo: str = ""               # "Relación de dependencia" | "Empleado público" | "Otro"
    alertas_empleo: List[str] = []

class PeriodoHaberes(BaseModel):
    """Un recibo de sueldo individual dentro del historial de 3 meses."""
    periodo: str = ""                   # MM/YYYY — ej: "07/2026"
    sueldo_bruto: str = ""              # Monto bruto del período
    sueldo_neto: str = ""               # Monto neto del período
    empleador: str = ""                 # Empleador declarado en ese recibo
    alertas: List[str] = []


class HaberesHistorico(BaseModel):
    """
    Historial de haberes de los últimos 3 meses.
    periodos[0] = más antiguo, periodos[-1] = más reciente.
    """
    periodos: List[PeriodoHaberes] = []
    promedio_neto_pesos: Optional[float] = None   # Promedio calculado de sueldo neto (numérico)
    tendencia: str = ""                           # "creciente" | "estable" | "decreciente"
    consistencia: str = ""                        # "OK" | "ALERTA" (empleador cambia entre recibos)


class ValidacionesIdentidad(BaseModel):
    nombres_coinciden: str = ""         # "OK" | "ALERTA" | "NO VERIFICABLE"
    detalle_coincidencia: str = ""      # Descripción de la comparación
    recibo_vigente: str = ""            # "OK" | "ALERTA: recibo de hace X meses"
    alertas_validacion: List[str] = []

class MetadatosProcesamiento(BaseModel):
    documentos_procesados: List[str] = []   # ["dni", "recibo_1", "recibo_2", "recibo_3"]
    metodo_extraccion: str = ""             
    alertas_generales: List[str] = []


SemaforoEstado = Literal["VERDE", "AMARILLO", "ROJO"]

class Recomendacion(BaseModel):
    estado: SemaforoEstado = "AMARILLO"         # VERDE / AMARILLO / ROJO
    decision: str = ""                          # "APROBAR" | "REVISAR" | "RECHAZAR"
    resumen: str = ""                           
    razones: List[str] = []                     
    condiciones_observadas: List[str] = []      
    requiere_revision_humana: bool = True       


class LoanApplicationExtractionResult(BaseModel):
    solicitante: Solicitante = Solicitante()
    empleo: Empleo = Empleo()
    haberes_historico: Optional[HaberesHistorico] = None   # Presente cuando hay 2+ recibos
    validaciones: ValidacionesIdentidad = ValidacionesIdentidad()
    recomendacion: Recomendacion = Recomendacion()
    metadatos: MetadatosProcesamiento = MetadatosProcesamiento()
