from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import resolve_current_user
from app.config import get_settings
from app.database.session import get_db
from app.services.auth_service import AuthService, AuthenticationError

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_secure() -> bool:
    return get_settings().environment.lower() == "production"


def _cookie_samesite() -> str:
    return get_settings().auth_cookie_samesite


@router.get("/login")
def login(db: Session = Depends(get_db)):
    try:
        return AuthService(db).login_redirect()
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="authentication unavailable"
        ) from error


@router.get("/callback")
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid authentication callback"
        )
    try:
        user, token = AuthService(db).callback(
            code, state, request.cookies.get(get_settings().auth_state_cookie_name, "")
        )
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="authentication failed"
        ) from error
    response = RedirectResponse(get_settings().auth_frontend_redirect_uri)
    response.delete_cookie(get_settings().auth_state_cookie_name, path="/auth")
    response.set_cookie(
        get_settings().auth_session_cookie_name,
        token,
        max_age=get_settings().auth_session_ttl_seconds,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )
    csrf_token = __import__("secrets").token_urlsafe(32)
    response.set_cookie(
        "personal_ai_os_csrf",
        csrf_token,
        max_age=get_settings().auth_session_ttl_seconds,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )
    return response


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    csrf_cookie = request.cookies.get("personal_ai_os_csrf")
    csrf_header = request.headers.get("x-csrf-token")
    if csrf_cookie and csrf_cookie != csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
    settings = get_settings()
    AuthService(db).logout(request.cookies.get(settings.auth_session_cookie_name))
    response = JSONResponse({"status": "ok"})
    response.delete_cookie(settings.auth_session_cookie_name, path="/")
    response.delete_cookie("personal_ai_os_csrf", path="/")
    return response


@router.get("/session")
def session(request: Request, db: Session = Depends(get_db)):
    try:
        user = resolve_current_user(request, db)
    except HTTPException:
        return {"authenticated": False}
    return {"authenticated": True, "user": {"id": user.id, "email": user.email}}
