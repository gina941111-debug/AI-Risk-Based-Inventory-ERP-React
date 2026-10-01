from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.access_control import RISK_ANALYSIS_READ, AccessContext
from backend.api.dependencies import require
from backend.llm_client import llm_available, complete_text


router = APIRouter(prefix="/copilot", tags=["copilot"])


class CopilotRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)


@router.post("/chat")
def chat(payload: CopilotRequest, principal: AccessContext = Depends(require(RISK_ANALYSIS_READ))):
    if not llm_available():
        raise HTTPException(status_code=503, detail="尚未設定 LLM_MODEL、OPENAI_API_KEY 或 GEMINI_API_KEY")
    answer = complete_text(
        payload.message,
        system="你是供應鏈風險分析助理。請優先說明風險、受影響範圍、證據與可執行的下一步。不要捏造資料。",
        tag="analysis:copilot",
    )
    return {"answer": answer, "actor": principal.username}
