# ------------------------------------------------------------------------------
#  Personas Controller — DemoBank Loan Application Asset
#  Handles the mock-persona workflow:
#    GET  /api/personas                   → list of applicant cards
#    GET  /api/personas/{id}/profile      → profile + 3-month payslip preview
#    GET  /api/personas/{id}/analyze      → SSE — AI analysis (3 recibos)
#    POST /api/personas/{id}/decision     → send decision email
# ------------------------------------------------------------------------------

import json
import asyncio
import traceback

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

from services.mock_data         import get_personas_list, get_persona_by_index
from services.payslip_generator import generate_payslip_text, generate_payslip_texts_3months, generate_dni_text
from services.extraction_service import extract_loan_entities
from services.email_service     import send_decision_email

router = APIRouter(
    prefix="/api/personas",
    tags=["Personas Workflow"],
)


# ------------------------------------------------------------------------------
#  GET /api/personas
#  Returns the summary list used to render the applicant cards.
# ------------------------------------------------------------------------------

@router.get("", response_description="List of mock applicant personas")
async def list_personas():
    return JSONResponse(content=get_personas_list())


# ------------------------------------------------------------------------------
#  GET /api/personas/{persona_id}/profile
#  Returns full persona profile + generated payslip text for the detail panel.
#  Lightweight — no AI involved.
# ------------------------------------------------------------------------------

@router.get(
    "/{persona_id}/profile",
    response_description="Full persona profile with generated payslip text",
)
async def get_persona_profile(persona_id: int):
    try:
        persona = get_persona_by_index(persona_id)
    except IndexError:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} no encontrada.")

    payslip_texts = await asyncio.to_thread(generate_payslip_texts_3months, persona)
    dni_text      = await asyncio.to_thread(generate_dni_text, persona)

    return JSONResponse(content={
        "id":            persona_id,
        "renaper":       persona["renaper"],
        "bcra":          persona["bcra"],
        "afip":          persona["afip"],
        "propiedad":     persona["propiedad"],
        "payslip_text":  payslip_texts[-1],   # most recent (backwards compat)
        "payslip_texts": payslip_texts,        # full 3-month list for UI preview
        "dni_text":      dni_text,
    })


# ------------------------------------------------------------------------------
#  GET /api/personas/{persona_id}/analyze
#  Generates mock payslip text + DNI text, runs the full AI extraction pipeline,
#  and streams SSE progress events identical to /api/loan/extract.
#  Final 'result' event includes persona_profile alongside the extraction data.
# ------------------------------------------------------------------------------

@router.get(
    "/{persona_id}/analyze",
    response_description="AI analysis of mock persona (SSE stream)",
)
async def analyze_persona(persona_id: int):
    try:
        persona = get_persona_by_index(persona_id)
    except IndexError:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} no encontrada.")

    async def event_stream():
        try:
            # --- Generate mock texts ---
            yield f"data: {json.dumps({'type': 'progress', 'step': 'generating', 'detail': 'Generando 3 recibos del solicitante…'})}\n\n"

            recibo_texts = await asyncio.to_thread(generate_payslip_texts_3months, persona)
            dni_text     = await asyncio.to_thread(generate_dni_text, persona)

            yield f"data: {json.dumps({'type': 'progress', 'step': 'extraction', 'detail': 'Analizando 3 meses de haberes con IA…'})}\n\n"

            # Build persona_profile upfront so the mortgage eligibility check
            # inside build_recommendation has access to the assigned property.
            persona_profile = {
                "renaper":   persona["renaper"],
                "bcra":      persona["bcra"],
                "afip":      persona["afip"],
                "propiedad": persona["propiedad"],
            }

            # --- Run AI extraction pipeline with 3 recibos ---
            entities = await asyncio.to_thread(
                extract_loan_entities,
                dni_text, "",              # recibo_text="" — use recibo_texts kwarg
                None, None, None,          # api_key, project_id, url — use env vars
                persona_profile,
                recibo_texts,              # list of 3 payslip texts (oldest first)
            )
            entities.setdefault("metadatos", {})["metodo_extraccion"] = "mock_text"

            if "error" in entities:
                yield f"data: {json.dumps({'type': 'error', 'detail': entities['error']})}\n\n"
                return

            entities["_persona_id"] = persona_id

            yield f"data: {json.dumps({'type': 'result', 'data': entities})}\n\n"

        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ------------------------------------------------------------------------------
#  POST /api/personas/{persona_id}/decision
#  Accepts a decision (aprobar/esperar/rechazar) and the AI result,
#  sends a decision email, and returns confirmation.
# ------------------------------------------------------------------------------

class DecisionRequest(BaseModel):
    decision: str               # 'aprobar' | 'esperar' | 'rechazar'
    ai_result: dict             # full extraction result from the analyze step
    razon: Optional[str] = ""   # optional free-text reason (not used currently)


@router.post(
    "/{persona_id}/decision",
    response_description="Send decision email to persona",
)
async def send_decision(persona_id: int, body: DecisionRequest):
    try:
        persona = get_persona_by_index(persona_id)
    except IndexError:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} no encontrada.")

    valid_decisions = {"aprobar", "esperar", "rechazar"}
    if body.decision.lower() not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Decisión inválida '{body.decision}'. Usar: aprobar, esperar o rechazar.",
        )

    # Send email asynchronously (non-blocking)
    result = await asyncio.to_thread(
        send_decision_email,
        persona,
        body.decision.lower(),
        body.ai_result,
    )

    return JSONResponse(content={
        "ok":            result.get("ok", False),
        "email_sent_to": persona["email"],
        "decision":      body.decision.lower(),
        "email_error":   result.get("error"),
    })
