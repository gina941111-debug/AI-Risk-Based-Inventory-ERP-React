"""
backend/auth.py
使用者驗證與角色型存取控制 (RBAC)
"""

from contextlib import contextmanager
from contextvars import ContextVar

from .database import run_query


_CURRENT_ROLE: ContextVar[str | None] = ContextVar("erp_current_role", default=None)
_CURRENT_ACTOR: ContextVar[str | None] = ContextVar("erp_current_actor", default=None)


@contextmanager
def authorization_context(role: str | None, actor: str | None = None):
    """Set request-local authorization data for legacy service functions.

    FastAPI uses capability checks directly, while older service functions still
    call ``check_permission``.  ContextVars keep those calls isolated per
    request and remove the former Streamlit session-state dependency.
    """
    role_token = _CURRENT_ROLE.set(role)
    actor_token = _CURRENT_ACTOR.set(actor)
    try:
        yield
    finally:
        _CURRENT_ROLE.reset(role_token)
        _CURRENT_ACTOR.reset(actor_token)


def current_actor() -> str | None:
    return _CURRENT_ACTOR.get()


def check_login(username: str, password: str) -> dict | None:
    """驗證帳號密碼，成功回傳 {role, name}，失敗回傳 None。
    （N3）密碼以 salted hash 比對；遇到 legacy 明文則於登入成功時就地升級。"""
    from backend.passwords import verify_password, is_hashed, hash_password

    rows = run_query(
        "SELECT password, role, name FROM users WHERE username=?",
        (username,),
    )
    if not rows:
        return None
    stored, role, name = rows[0]
    if not verify_password(password, stored or ""):
        return None
    if not is_hashed(stored or ""):  # legacy 明文 → 自我修復式升級
        run_query("UPDATE users SET password=? WHERE username=?",
                  (hash_password(password), username), fetch=False)
    return {"role": role, "name": name}


def check_permission(allowed_roles: list) -> bool:
    """依目前 request-local 角色判斷權限；沒有上下文時一律拒絕。"""
    current_role = _CURRENT_ROLE.get()
    if current_role == "admin":
        return True
    return current_role in allowed_roles
