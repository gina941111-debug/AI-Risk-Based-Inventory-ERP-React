from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.access_control import (
    RISK_ANALYSIS_READ,
    RISK_OVERVIEW_READ,
    RISK_WHAT_IF_RUN,
    RISK_WORKSPACE_WRITE,
    AccessContext,
)
from backend.api.dependencies import get_current_principal, require
from backend.api.serializers import records
from backend.database import DB_FILE
from backend import supply_chain_risk as risk


router = APIRouter(prefix="/risk", tags=["risk"])


class RiskEventRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    region: str = Field(default="", max_length=120)
    country: str = Field(default="", max_length=120)
    impact_days: int = Field(default=0, ge=0, le=365)
    description: str = Field(default="", max_length=2000)


class WhatIfRequest(BaseModel):
    question: str = Field(min_length=5, max_length=4000)


@router.get("/dashboard", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def dashboard():
    return {
        "kpis": risk.get_supply_chain_summary_kpis(),
        "heatmap": records(risk.get_risk_heatmap_data()),
        "events": records(risk.get_risk_events_list(limit=10)),
        "region_procurement_share": records(risk.get_region_procurement_share()),
    }


@router.get("/heatmap", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def heatmap():
    return {"items": records(risk.get_risk_heatmap_data())}


@router.get("/events", dependencies=[Depends(require(RISK_OVERVIEW_READ))])
def events(limit: int = Query(default=50, ge=1, le=200)):
    return {"items": records(risk.get_risk_events_list(limit=limit))}


@router.post("/events", status_code=201)
def create_event(payload: RiskEventRequest, principal: AccessContext = Depends(require(RISK_WORKSPACE_WRITE))):
    event_id = risk.add_risk_event(
        payload.event_type, payload.region, payload.country, payload.impact_days,
        payload.description, actor=principal.username,
    )
    return {"id": event_id}


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, principal: AccessContext = Depends(require(RISK_WORKSPACE_WRITE))):
    risk.delete_risk_event(event_id, actor=principal.username)


@router.get("/events/{event_id}/impact", dependencies=[Depends(require(RISK_ANALYSIS_READ))])
def event_impact(event_id: int):
    row = sqlite3.connect(DB_FILE)
    item = row.execute(
        "SELECT id, event_type, region, country, impact_days, description, created_at FROM supply_chain_events WHERE id=?",
        (event_id,),
    ).fetchone()
    row.close()
    if item is None:
        raise HTTPException(status_code=404, detail="找不到風險事件")
    _, event_type, region, country, impact_days, description, created_at = item
    return {
        "event": {"id": event_id, "event_type": event_type, "region": region,
                  "country": country, "impact_days": impact_days, "description": description,
                  "created_at": created_at},
        "suppliers": records(risk.get_affected_suppliers_by_event(region or "", country)),
        "orders": records(risk.get_affected_sales_orders_by_event(region or "", country or "", impact_days or 0)),
        "stockout_alerts": records(risk.get_stockout_alerts_for_event(region or "", country or "", impact_days or 0)),
    }


@router.post("/what-if", dependencies=[Depends(require(RISK_WHAT_IF_RUN))])
def what_if(payload: WhatIfRequest, principal: AccessContext = Depends(require(RISK_WHAT_IF_RUN))):
    text = risk.what_if_simulation("", payload.question, actor=principal.username)
    return {"answer": text, "ai_configured": not text.startswith("模擬分析暫時無法產生")}
