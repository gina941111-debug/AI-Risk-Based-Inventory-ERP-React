from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.api.routes import agents, auth, copilot, data, risk


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Supply Chain Risk API",
    version="0.1.0",
    description="AI-first supply-chain risk workspace API; ERP data is the evidence layer.",
    lifespan=lifespan,
)

origins = [item.strip() for item in os.getenv("API_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")
app.include_router(copilot.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")


@app.get("/healthz", tags=["system"])
def healthz():
    return {"status": "ok", "service": "risk-api"}
