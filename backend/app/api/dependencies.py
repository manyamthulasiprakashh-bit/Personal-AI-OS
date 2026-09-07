from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.config import get_settings
from app.models.user import User
from app.models.auth import AuthSession


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


def get_current_user(db: Session = Depends(get_db), request: Request = None) -> CurrentUser:
    if request is not None:
        return resolve_current_user(request, db)

    settings = get_settings()
    if getattr(settings, "environment", "test").lower() not in {"development", "test"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required"
        )

    configured_email = settings.development_user_email.strip()
    if not configured_email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="development user is not configured",
        )
    user = db.execute(select(User).where(User.email == configured_email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="configured development user does not exist",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="configured development user is inactive"
        )
    return CurrentUser(id=user.id, email=user.email)


def resolve_current_user(request: Request, db: Session) -> CurrentUser:
    """Resolve a production session, with no production development fallback."""
    settings = get_settings()
    token = request.cookies.get(settings.auth_session_cookie_name)
    now = datetime.now(timezone.utc)
    if token:
        session_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        session = db.execute(
            select(AuthSession).where(
                AuthSession.session_hash == session_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
        ).scalar_one_or_none()
        if session is not None and session.user.is_active:
            session.last_used_at = now
            db.commit()
            return CurrentUser(id=session.user.id, email=session.user.email)

    if (
        settings.environment.lower() in {"development", "test"}
        and settings.auth_mode == "development"
    ):
        configured_email = settings.development_user_email.strip()
        if configured_email:
            user = db.execute(
                select(User).where(User.email == configured_email)
            ).scalar_one_or_none()
            if user is not None and user.is_active:
                return CurrentUser(id=user.id, email=user.email)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="authentication required",
        headers={"WWW-Authenticate": "Session"},
    )
