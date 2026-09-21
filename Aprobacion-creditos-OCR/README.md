# Aprobación de Créditos — OCR con IA

Sistema que extrae datos estructurados de documentos PDF (DNI y recibos de sueldo) para asistir al analista bancario en la evaluación de solicitudes de crédito hipotecario.

---

## Stack

- **Backend**: Python, FastAPI
- **IA**: IBM Watsonx.ai — Mistral Vision (OCR) + GPT-OSS-120B (extracción)
- **Frontend**: HTML/CSS/JS estático servido por FastAPI

---

## ¿Cómo funciona?

```
PDF(s) → OCR Vision (Mistral) → Extracción de entidades (GPT-120B) → JSON + Alertas
```

Hay tres modos de uso:

| Endpoint | Cuándo usarlo |
|----------|--------------|
| `POST /api/loan/extract` | PDFs escaneados o fotos — usa visión IA |
| `POST /api/loan/extract-digital` | PDFs digitales — extrae texto con PyMuPDF (sin costo de OCR) |
| `POST /api/loan/extract-from-text` | Texto ya disponible — solo corre la extracción |

El resultado es un JSON con datos del solicitante, empleo, validación cruzada de identidad y una recomendación con semáforo (APROBAR / REVISAR / RECHAZAR).

---

## Modelos de IA

| Rol | Modelo | Notas |
|-----|--------|-------|
| OCR | `mistralai/mistral-medium-2505` | Convierte imágenes de páginas PDF a texto. Temperature `0` |
| Extracción | `openai/gpt-oss-120b` | Estructura el texto en JSON. Temperature `0.1` |

Ambos corren sobre **IBM Watsonx.ai**.

---

## Setup

**1. Configurar variables de entorno**
```bash
cp .env.example .env
# Completar con las credenciales de IBM Watsonx.ai
```

**2. Instalar dependencias**
```bash
pip install -r requirements.txt
```

> **macOS/Linux**: `pdf2image` requiere `poppler`:
> ```bash
> brew install poppler       # macOS
> apt install poppler-utils  # Ubuntu/Debian
> ```

**3. Correr el servidor**
```bash
python app.py
```

Abrí `http://localhost:4051` en el navegador.

---

## Variables de entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `WATSONX_API_KEY` | IBM Cloud API Key | ✅ |
| `WATSONX_PROJECT_ID` | Watsonx.ai project ID | ✅ |
| `WATSONX_URL` | Base URL de Watsonx.ai | ✅ (default: `us-south.ml.cloud.ibm.com`) |
| `GMAIL_USER` | Cuenta Gmail para envío de notificaciones | ❌ |
| `GMAIL_APP_PASSWORD` | App password de Gmail | ❌ |
| `PORT_FASTAPI` | Puerto del servidor | ❌ (default: `4051`) |

---

## Estructura

```
Aprobacion-creditos-OCR/
├── app.py                          ← Entry point FastAPI
├── requirements.txt
├── .env.example
├── models/
│   └── schemas.py                  ← Pydantic data models
├── routers/
│   ├── loan_extraction_controller.py  ← Endpoints de extracción
│   └── personas_controller.py         ← Endpoints del workflow demo
├── services/
│   ├── transcription_service.py    ← OCR con Mistral Vision + PyMuPDF
│   ├── extraction_service.py       ← Extracción de entidades con GPT
│   ├── recommendation_service.py   ← Lógica de recomendación crediticia
│   ├── email_service.py            ← Notificaciones por email
│   ├── mock_data.py                ← Personas demo para el workflow
│   └── payslip_generator.py        ← Generador de recibos mock
└── ui/                             ← Frontend estático
```
