from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status

from backend.access_control import AccessContext, require_capability
from backend.auth import authorization_context
from backend.api.session_store import sessions


def get_current_principal(session_token: str | None = Cookie(default=None)) -> AccessContext:
    session = sessions.get(session_token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="請先登入")
    from backend.access_control import load_principal

    principal = load_principal(session.username)
    if principal is None:
        sessions.delete(session_token)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號已失效")
    return principal


def require(capability: str):
    def dependency(principal: AccessContext = Depends(get_current_principal)) -> AccessContext:
        try:
            require_capability(principal.username, capability)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return principal

    return dependency


class AuthorizationContext:
    """Dependency helper to keep legacy role checks request-local."""

    def __init__(self, principal: AccessContext):
        self.principal = principal

    def __enter__(self):
        self._context = authorization_context(self.principal.role, self.principal.username)
        self._context.__enter__()
        return self.principal

    def __exit__(self, *args):
        return self._context.__exit__(*args)
