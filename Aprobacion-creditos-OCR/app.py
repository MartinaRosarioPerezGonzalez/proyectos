# Environment setup
from dotenv import load_dotenv
load_dotenv()

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="DemoBank Loan Application — AI Entity Extraction",
    description=(
        "API for extracting structured entities from DemoBank loan application documents "
        "(DNI + payslip) using IBM watsonx.ai multimodal models."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes first
from routers import loan_extraction_controller, personas_controller
app.include_router(loan_extraction_controller.router)
app.include_router(personas_controller.router)

# Serve UI static files after API routes
ui_dir = os.path.join(os.path.dirname(__file__), "ui")
if os.path.isdir(ui_dir):
    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT_FASTAPI", 4051)),
        reload=True,
    )
