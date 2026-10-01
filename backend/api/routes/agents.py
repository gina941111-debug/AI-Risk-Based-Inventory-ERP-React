from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.access_control import (
    APPROVAL_DECIDE,
    APPROVAL_QUEUE_READ,
    ERP_EXCHANGE_PROPOSE,
    PROPOSAL_EVIDENCE_READ,
    RISK_ANALYSIS_READ,
    AccessContext,
)
from backend.agent_logger import approve_action, get_action_logs, get_pending_approvals, reject_action
from backend.agent_registry import AGENTS, get_agent_for_tool, get_tools_for_agent
from backend.api.dependencies import get_current_principal, require
from backend.database import run_query
from backend.dispatch_logger import get_recent_dispatches
from backend.purchase_proposals import (
    ApprovalDecision,
    decide_purchase_proposal,
    get_purchase_operation_timeline,
    get_purchase_proposal_evidence,
    list_alternative_suppliers,
    list_impacted_purchase_options,
    prepare_alternative_purchase_proposal,
    submit_purchase_proposal,
)


router = APIRouter(prefix="/agents", tags=["agents"])


def dashboard_access(principal: AccessContext = Depends(get_current_principal)) -> AccessContext:
    if not (principal.can(RISK_ANALYSIS_READ) or principal.can(APPROVAL_QUEUE_READ) or principal.can(PROPOSAL_EVIDENCE_READ)):
        raise HTTPException(status_code=403, detail="使用者沒有 Agent Dashboard 權限")
    return principal


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    history: list[dict] = Field(default_factory=list)
    use_llm: bool = True


class ApprovalDecisionRequest(BaseModel):
    outcome: str = Field(pattern="^(approve|reject)$")
    reason: str = Field(default="", max_length=1000)


class ProposalRequest(BaseModel):
    affected_po_id: str = Field(min_length=1, max_length=80)
    product_id: str = Field(min_length=1, max_length=80)
    source_po_item_id: int | None = Field(default=None, gt=0)
    alternative_supplier_id: str = Field(min_length=1, max_length=80)
    alternative_supplier_product_id: int | None = Field(default=None, gt=0)
    reason: str = Field(min_length=1, max_length=1000)
    proposal_id: str = Field(min_length=1, max_length=80)
    estimated_delay_days: int | None = Field(default=None, ge=0, le=365)
    source_event_id: int | None = Field(default=None, gt=0)


def _agent_view(agent_id: str, meta: dict) -> dict:
    return {
        "id": agent_id,
        "name_zh": meta.get("name_zh", agent_id),
        "name_en": meta.get("name_en", agent_id),
        "description": meta.get("description", ""),
        "modules": meta.get("modules", []),
        "can_write": bool(meta.get("can_write")),
        "tools": get_tools_for_agent(agent_id),
    }


@router.get("/overview")
def overview(principal: AccessContext = Depends(dashboard_access)):
    """React Agent Dashboard 的總覽資料；包含 8 個 Agent，但不建立財務／人資工作區。"""
    return {
        "agents": [_agent_view(agent_id, meta) for agent_id, meta in AGENTS.items()],
        "actor": principal.username,
        "role": principal.role,
    }


@router.get("/dispatch-logs")
def dispatch_logs(
    limit: int = Query(default=50, ge=1, le=200),
    _: AccessContext = Depends(dashboard_access),
):
    return {"items": get_recent_dispatches(limit=limit)}


@router.get("/action-logs")
def action_logs(
    limit: int = Query(default=50, ge=1, le=200),
    _: AccessContext = Depends(dashboard_access),
):
    items = get_action_logs(limit=limit)
    for item in items:
        item["agent"] = get_agent_for_tool(item.get("tool_name", ""))
    return {"items": items}


@router.get("/approvals")
def approvals(
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    _: AccessContext = Depends(require(APPROVAL_QUEUE_READ)),
):
    return {"items": get_pending_approvals(status_filter=status)}


@router.post("/approvals/{approval_id}/decision")
def approval_decision(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    principal: AccessContext = Depends(require(APPROVAL_DECIDE)),
):
    try:
        approval = next(
            (item for item in get_pending_approvals() if item["approval_id"] == approval_id),
            None,
        )
        if approval is None:
            raise HTTPException(status_code=404, detail="找不到審批項目")
        operation_id = approval.get("operation_id") or ""
        # Purchase Proposal 的審批必須走其完整性驗證與 Gateway adapter。
        if operation_id.startswith("proposal:create-po:"):
            proposal_id = operation_id.removeprefix("proposal:create-po:").removesuffix(":v1")
            result = decide_purchase_proposal(
                ApprovalDecision(proposal_id=proposal_id, outcome=payload.outcome, reason=payload.reason),
                actor=principal.username,
            )
        elif payload.outcome == "approve":
            result = approve_action(approval_id, approver=principal.username)
        else:
            if not payload.reason.strip():
                raise HTTPException(status_code=400, detail="拒絕審批必須填寫原因")
            result = reject_action(approval_id, payload.reason, approver=principal.username)
        return {"ok": True, "result": result}
    except HTTPException:
        raise
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/proposals/options")
def proposal_options(principal: AccessContext = Depends(require(ERP_EXCHANGE_PROPOSE))):
    try:
        return {"items": list_impacted_purchase_options(actor=principal.username)}
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/proposals")
def proposals(
    limit: int = Query(default=50, ge=1, le=200),
    principal: AccessContext = Depends(dashboard_access),
):
    rows = run_query(
        """
        SELECT proposal_id, proposer_username, proposer_role, affected_po_id,
               proposed_po_id, original_supplier_id, alternative_supplier_id,
               product_id, qty, unit_price, proposed_status, reason, created_at,
               organization_id
        FROM purchase_proposals
        WHERE organization_id = ?
          AND (? = 1 OR proposer_username = ?)
        ORDER BY created_at DESC LIMIT ?
        """,
        (principal.organization_id, int(principal.can(PROPOSAL_EVIDENCE_READ)), principal.username, limit),
    )
    return {
        "items": [
            {
                "proposal_id": row[0], "proposer_username": row[1], "proposer_role": row[2],
                "affected_po_id": row[3], "proposed_po_id": row[4],
                "original_supplier_id": row[5], "alternative_supplier_id": row[6],
                "product_id": row[7], "qty": row[8], "unit_price": row[9],
                "proposed_status": row[10], "reason": row[11], "created_at": row[12],
            }
            for row in rows
        ]
    }


@router.get("/proposals/{proposal_id}")
def proposal_evidence(proposal_id: str, principal: AccessContext = Depends(dashboard_access)):
    try:
        proposal = get_purchase_proposal_evidence(proposal_id, actor=principal.username)
        if proposal is None:
            raise HTTPException(status_code=404, detail="找不到採購提案")
        operation_id = f"proposal:create-po:{proposal_id}:v1"
        timeline = []
        if principal.can(PROPOSAL_EVIDENCE_READ):
            timeline = get_purchase_operation_timeline(operation_id, actor=principal.username)
        return {"proposal": asdict(proposal), "timeline": timeline}
    except HTTPException:
        raise
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/proposals/{proposal_id}/suppliers")
def proposal_suppliers(
    proposal_id: str,
    affected_po_id: str,
    product_id: str,
    principal: AccessContext = Depends(require(ERP_EXCHANGE_PROPOSE)),
):
    try:
        return {"items": list_alternative_suppliers(affected_po_id=affected_po_id, product_id=product_id, actor=principal.username)}
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/proposals", status_code=201)
def create_proposal(payload: ProposalRequest, principal: AccessContext = Depends(require(ERP_EXCHANGE_PROPOSE))):
    try:
        proposal = prepare_alternative_purchase_proposal(**payload.model_dump(), actor=principal.username)
        result = submit_purchase_proposal(proposal, actor=principal.username)
        return {"proposal": asdict(proposal), "result": result}
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/manufacturing")
def manufacturing(_: AccessContext = Depends(dashboard_access)):
    bom_rows = run_query("SELECT id, product_id, component_id, qty_per FROM bom ORDER BY id DESC LIMIT 100")
    work_rows = run_query("SELECT wo_id, product_id, qty_plan, qty_done, status, start_date, end_date FROM work_orders ORDER BY start_date DESC LIMIT 100")
    return {
        "bom": [{"id": row[0], "product_id": row[1], "component_id": row[2], "qty_per": row[3]} for row in bom_rows],
        "work_orders": [{"wo_id": row[0], "product_id": row[1], "qty_plan": row[2], "qty_done": row[3], "status": row[4], "start_date": row[5], "end_date": row[6]} for row in work_rows],
    }


@router.post("/chat")
def agent_chat(payload: AgentChatRequest, principal: AccessContext = Depends(require(RISK_ANALYSIS_READ))):
    # LiteLLM is optional for the data/governance API. Load it only when the
    # user opens the cross-agent chat so the rest of React still works in an
    # offline virtual-data environment.
    try:
        from backend.agent_orchestrator import orchestrate
    except ModuleNotFoundError as exc:
        # Local virtual-data installs may intentionally omit optional LLM
        # packages. Keep the dashboard usable with deterministic keyword
        # routing and make the limitation explicit in the response.
        from backend.agent_registry import get_agent, route_by_keyword
        from backend.dispatch_logger import write_dispatch_log

        agent_id = route_by_keyword(payload.message)
        routing = {
            "task_type": "single",
            "primary_agent": agent_id,
            "agent_chain": [agent_id],
            "needs_approval": False,
            "reason": "離線關鍵字路由",
            "routed_by": "keyword-fallback",
        }
        write_dispatch_log(routing, payload.message, caller=principal.role)
        name = (get_agent(agent_id) or {}).get("name_zh", agent_id)
        return {
            "routing": routing,
            "results": [],
            "pending": [],
            "reply": f"[離線模式] 已將任務路由給「{name}」。安裝 LiteLLM 並設定模型金鑰後即可執行 Agent 工具。",
        }
    result = orchestrate(
        payload.message,
        role=principal.role,
        use_llm=payload.use_llm,
        history=payload.history[-8:],
        actor=principal.username,
    )
    return result
