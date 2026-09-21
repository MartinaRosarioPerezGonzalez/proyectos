# ------------------------------------------------------------------------------
#  Loan Extraction Controller — DemoBank Loan Application Asset
#  Handles PDF upload, transcription routing, entity extraction, and response.
#
#  Multi-recibo support (3 payslips):
#    POST /api/loan/extract        → recibo_1, recibo_2, recibo_3 (+ legacy alias recibo)
#    POST /api/loan/extract-digital → same
#    POST /api/loan/extract-from-text → recibo_text_1, recibo_text_2, recibo_text_3
# ------------------------------------------------------------------------------

import json
import traceback
import asyncio
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from fastapi.responses import JSONResponse, StreamingResponse

from services.transcription_service import (
    transcribe_pdf_from_bytes,
    extract_text_from_pdf_bytes,
)
from services.extraction_service import extract_loan_entities

router = APIRouter(
    prefix="/api/loan",
    tags=["DemoBank Loan Application Extraction"],
    responses={404: {"description": "Not found"}},
)


# ------------------------------------------------------------------------------
#  POST /api/loan/extract
#  Full pipeline: AI transcription (Mistral) + entity extraction (GPT)
#  Accepts up to 3 payslip PDFs: recibo_1, recibo_2, recibo_3 (oldest → newest).
#  Legacy param `recibo` is treated as alias for recibo_1.
# ------------------------------------------------------------------------------

@router.post(
    "/extract",
    response_description="Extract loan application entities from uploaded PDFs (full AI pipeline)",
)
async def extract_loan_application(
    dni:      Optional[UploadFile] = File(None, description="PDF o imagen del DNI del solicitante"),
    recibo:   Optional[UploadFile] = File(None, description="(legacy) PDF del recibo de sueldo — alias de recibo_1"),
    recibo_1: Optional[UploadFile] = File(None, description="PDF del recibo de sueldo más antiguo (mes -2)"),
    recibo_2: Optional[UploadFile] = File(None, description="PDF del recibo de sueldo intermedio (mes -1)"),
    recibo_3: Optional[UploadFile] = File(None, description="PDF del recibo de sueldo más reciente"),
):
    """
    Full AI pipeline for loan document processing.

    Steps:
      1. Convert each PDF page to image (PyMuPDF)
      2. Transcribe each page with Mistral Vision (Watsonx.ai)
      3. Extract structured entities with GPT-OSS-120B (Watsonx.ai)
      4. Cross-validate identity (DNI name vs payslip name)

    Returns Server-Sent Events (SSE) with progress updates.
    Final event contains the complete JSON result.

    Accepts up to 3 payslip PDFs (recibo_1, recibo_2, recibo_3) ordered from
    oldest to most recent. `recibo` is kept as a legacy alias for recibo_1.
    At least one of `dni` or any recibo must be provided.
    """
    # Resolve legacy alias: `recibo` → recibo_1 if recibo_1 not provided
    if recibo and not recibo_1:
        recibo_1 = recibo

    recibo_uploads = [r for r in [recibo_1, recibo_2, recibo_3] if r is not None]

    if not dni and not recibo_uploads:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos un documento (DNI o recibo de sueldo).",
        )

    # Read all bytes before entering the async generator
    dni_bytes      = await dni.read() if dni else None
    recibo_bytes_list = []
    for r in recibo_uploads:
        recibo_bytes_list.append(await r.read())

    async def event_stream():
        progress_events: list[str] = []

        def send(step: str, detail: str):
            progress_events.append(
                f"data: {json.dumps({'type': 'progress', 'step': step, 'detail': detail})}\n\n"
            )

        try:
            # --- Transcribe DNI ---
            dni_text = ""
            if dni_bytes:
                send("transcription_dni", "Transcribiendo DNI con IA…")
                yield progress_events.pop(0)
                dni_text = await asyncio.to_thread(
                    transcribe_pdf_from_bytes,
                    dni_bytes, None, None,
                    "mistralai/mistral-medium-2505", None, 200,
                    lambda step, detail: send(step, detail),
                )
                while progress_events:
                    yield progress_events.pop(0)

            # --- Transcribe each Recibo ---
            recibo_texts = []
            total = len(recibo_bytes_list)
            for idx, rb in enumerate(recibo_bytes_list):
                num = idx + 1
                send("transcription_recibo", f"Transcribiendo recibo {num} de {total} con IA…")
                yield progress_events.pop(0)
                text = await asyncio.to_thread(
                    transcribe_pdf_from_bytes,
                    rb, None, None,
                    "mistralai/mistral-medium-2505", None, 200,
                    lambda step, detail: send(step, detail),
                )
                while progress_events:
                    yield progress_events.pop(0)
                recibo_texts.append(text)

            # --- Extract entities ---
            yield f"data: {json.dumps({'type': 'progress', 'step': 'extraction', 'detail': 'Extrayendo entidades con IA…'})}\n\n"
            entities = await asyncio.to_thread(
                extract_loan_entities,
                dni_text, "",           # recibo_text="" — we use recibo_texts kwarg
                None, None, None,       # api_key, project_id, url — use env vars
                None,                   # persona_profile
                recibo_texts,           # recibo_texts list
            )
            entities.setdefault("metadatos", {})["metodo_extraccion"] = "vision_ai"

            if "error" in entities:
                yield f"data: {json.dumps({'type': 'error', 'detail': entities['error']})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'result', 'data': entities})}\n\n"

        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ------------------------------------------------------------------------------
#  POST /api/loan/extract-digital
#  Fast pipeline: PyMuPDF text extraction (free) + GPT entity extraction
#  Accepts up to 3 payslip PDFs. Same parameter convention as /extract.
# ------------------------------------------------------------------------------

@router.post(
    "/extract-digital",
    response_description="Extract loan entities from digital PDFs (no AI transcription)",
)
async def extract_loan_application_digital(
    dni:      Optional[UploadFile] = File(None, description="PDF digital del DNI"),
    recibo:   Optional[UploadFile] = File(None, description="(legacy) PDF del recibo de sueldo — alias de recibo_1"),
    recibo_1: Optional[UploadFile] = File(None, description="PDF digital del recibo más antiguo"),
    recibo_2: Optional[UploadFile] = File(None, description="PDF digital del recibo intermedio"),
    recibo_3: Optional[UploadFile] = File(None, description="PDF digital del recibo más reciente"),
):
    """
    Fast extraction pipeline for digital PDFs.

    Steps:
      1. Extract embedded text from PDF using PyMuPDF (instant, free, no tokens)
      2. Extract structured entities with GPT-OSS-120B (Watsonx.ai)

    Accepts up to 3 payslip PDFs ordered from oldest to most recent.
    Use this endpoint when documents are generated by software (not scanned).
    For scanned/photo documents, use POST /api/loan/extract instead.
    """
    # Resolve legacy alias
    if recibo and not recibo_1:
        recibo_1 = recibo

    recibo_uploads = [r for r in [recibo_1, recibo_2, recibo_3] if r is not None]

    if not dni and not recibo_uploads:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos un documento (DNI o recibo de sueldo).",
        )

    try:
        # Extract DNI text
        dni_text = ""
        if dni:
            dni_bytes = await dni.read()
            result = await asyncio.to_thread(extract_text_from_pdf_bytes, dni_bytes)
            if not result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error extrayendo texto del DNI: {result.get('error')}",
                )
            dni_text = result["text"]

        # Extract each recibo text
        recibo_texts = []
        for idx, r in enumerate(recibo_uploads):
            rb = await r.read()
            result = await asyncio.to_thread(extract_text_from_pdf_bytes, rb)
            if not result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error extrayendo texto del recibo {idx + 1}: {result.get('error')}",
                )
            recibo_texts.append(result["text"])

        # Entity extraction (GPT only)
        entities = await asyncio.to_thread(
            extract_loan_entities,
            dni_text, "",           # recibo_text="" — we use recibo_texts kwarg
            None, None, None,       # api_key, project_id, url
            None,                   # persona_profile
            recibo_texts,
        )
        entities.setdefault("metadatos", {})["metodo_extraccion"] = "pymupdf"

        if "error" in entities:
            raise HTTPException(status_code=500, detail=entities["error"])

        return JSONResponse(content=entities)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en extracción: {e}")


# ------------------------------------------------------------------------------
#  POST /api/loan/extract-from-text
#  Direct extraction from pre-transcribed text — no PDF processing at all.
#  Accepts up to 3 recibo texts: recibo_text_1, recibo_text_2, recibo_text_3.
#  Legacy `recibo_text` is kept as alias for recibo_text_1.
# ------------------------------------------------------------------------------

@router.post(
    "/extract-from-text",
    response_description="Extract loan entities from provided text",
)
async def extract_from_text(
    dni_text:      Optional[str] = Form("", description="Texto del DNI ya transcripto"),
    recibo_text:   Optional[str] = Form("", description="(legacy) Texto del recibo — alias de recibo_text_1"),
    recibo_text_1: Optional[str] = Form("", description="Texto del recibo más antiguo ya transcripto"),
    recibo_text_2: Optional[str] = Form("", description="Texto del recibo intermedio ya transcripto"),
    recibo_text_3: Optional[str] = Form("", description="Texto del recibo más reciente ya transcripto"),
):
    """
    Extract loan entities directly from text (no PDF handling).

    Use this endpoint for:
    - Testing the extraction prompt without uploading files
    - Benchmarking token consumption of the extraction model in isolation
    - Integrations where transcription is done externally

    Accepts up to 3 recibo texts ordered oldest → newest.
    Legacy `recibo_text` is treated as alias for recibo_text_1.
    """
    # Resolve legacy alias
    if recibo_text and not recibo_text_1:
        recibo_text_1 = recibo_text

    recibo_texts = [t for t in [recibo_text_1, recibo_text_2, recibo_text_3] if t and t.strip()]

    if not dni_text and not recibo_texts:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos uno de los textos (dni_text o recibo_text_1).",
        )

    try:
        entities = await asyncio.to_thread(
            extract_loan_entities,
            dni_text or "", "",     # recibo_text="" — we use recibo_texts kwarg
            None, None, None,       # api_key, project_id, url
            None,                   # persona_profile
            recibo_texts,
        )
        entities.setdefault("metadatos", {})["metodo_extraccion"] = "text_input"

        if "error" in entities:
            raise HTTPException(status_code=500, detail=entities["error"])

        return JSONResponse(content=entities)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en extracción: {e}")
