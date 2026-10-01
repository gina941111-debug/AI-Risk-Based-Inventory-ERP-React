from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
from threading import RLock


@dataclass(frozen=True)
class Session:
    username: str
    expires_at: datetime


class SessionStore:
    """Small in-memory session store for the local MVP.

    This is intentionally process-local for the pre-container review. Before
    production or multiple replicas, replace it with Redis/database-backed
    sessions and rotate the signing/CSRF strategy.
    """

    def __init__(self, ttl_minutes: int = 480):
        self.ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict[str, Session] = {}
        self._lock = RLock()

    def create(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = Session(username, datetime.now(timezone.utc) + self.ttl)
        return token

    def get(self, token: str | None) -> Session | None:
        if not token:
            return None
        now = datetime.now(timezone.utc)
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None
            if session.expires_at <= now:
                self._sessions.pop(token, None)
                return None
            return session

    def delete(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessions.pop(token, None)


sessions = SessionStore()
