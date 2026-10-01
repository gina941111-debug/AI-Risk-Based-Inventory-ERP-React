from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel, Field

from backend.auth import check_login
from backend.access_control import load_principal
from backend.api.session_store import sessions


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    result = check_login(payload.username.strip(), payload.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤")
    principal = load_principal(payload.username.strip())
    if principal is None:
        raise HTTPException(status_code=403, detail="帳號尚未完成組織與方案設定")
    token = sessions.create(principal.username)
    response.set_cookie(
        "session_token", token, httponly=True, samesite="lax", secure=False, max_age=8 * 60 * 60
    )
    return {"username": principal.username, "name": principal.name, "role": principal.role,
            "capabilities": sorted(principal.capabilities)}


@router.post("/logout", status_code=204)
def logout(response: Response, session_token: str | None = Cookie(default=None)):
    sessions.delete(session_token)
    response.delete_cookie("session_token")


@router.get("/me")
def me(session_token: str | None = Cookie(default=None)):
    session = sessions.get(session_token)
    if session is None:
        raise HTTPException(status_code=401, detail="請先登入")
    principal = load_principal(session.username)
    if principal is None:
        sessions.delete(session_token)
        raise HTTPException(status_code=401, detail="帳號已失效")
    return {"username": principal.username, "name": principal.name, "role": principal.role,
            "organization_id": principal.organization_id,
            "capabilities": sorted(principal.capabilities)}
