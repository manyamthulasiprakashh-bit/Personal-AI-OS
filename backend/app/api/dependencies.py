from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.config import get_settings
from app.models.user import User


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


def get_current_user(db: Session = Depends(get_db)) -> CurrentUser:
    configured_email = get_settings().development_user_email.strip()
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="configured development user is inactive",
        )
    return CurrentUser(id=user.id, email=user.email)
