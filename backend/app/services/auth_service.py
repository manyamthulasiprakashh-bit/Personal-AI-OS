from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from authlib.jose import jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.auth import AuthSession, AuthTransaction, UserIdentity
from app.models.user import User


class AuthenticationError(RuntimeError):
    pass


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC.

    SQLite-backed ``DateTime(timezone=True)`` columns may reload as naive
    datetimes in tests; treat those as UTC rather than raising when compared
    against ``datetime.now(timezone.utc)``. Aware datetimes are converted to
    UTC. The represented instant is never altered.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()

    @property
    def issuer(self) -> str:
        return self.settings.auth0_issuer.rstrip("/")

    def _require_oidc(self) -> None:
        if self.settings.environment.lower() == "production" and self.settings.auth_mode != "oidc":
            raise AuthenticationError("production authentication is not configured")
        if self.settings.auth_mode != "oidc":
            raise AuthenticationError("OIDC authentication is not enabled")
        if not all((self.issuer, self.settings.auth0_client_id, self.settings.auth0_redirect_uri)):
            raise AuthenticationError("OIDC authentication is not configured")
        if self.settings.environment.lower() == "production":
            if not self.settings.auth0_client_secret.strip():
                raise AuthenticationError("OIDC client secret is not configured")
            if not self.settings.auth0_redirect_uri.startswith("https://"):
                raise AuthenticationError("production OIDC redirect must use HTTPS")
            if self.settings.secret_key == "change-me-in-production":
                raise AuthenticationError("production secret key is not configured")

    def _metadata(self) -> dict:
        self._require_oidc()
        try:
            response = httpx.get(f"{self.issuer}/.well-known/openid-configuration", timeout=10)
            response.raise_for_status()
            metadata = response.json()
            if not isinstance(metadata, dict):
                raise ValueError
            if metadata.get("issuer", "").rstrip("/") != self.issuer:
                raise ValueError
            return metadata
        except Exception as error:
            raise AuthenticationError("OIDC discovery failed") from error

    def _seal_state(self, payload: dict) -> str:
        encoded = (
            base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            .rstrip(b"=")
            .decode("ascii")
        )
        signature = hmac.new(
            self.settings.secret_key.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
        ).hexdigest()
        return f"{encoded}.{signature}"

    def _unseal_state(self, value: str) -> dict:
        try:
            encoded, signature = value.split(".", 1)
            expected = hmac.new(
                self.settings.secret_key.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError
            padded = encoded + "=" * (-len(encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            if int(payload["expires_at"]) < int(datetime.now(timezone.utc).timestamp()):
                raise ValueError
            return payload
        except Exception as error:
            raise AuthenticationError("invalid authentication state") from error

    def login_redirect(self):
        metadata = self._metadata()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.settings.auth_state_ttl_seconds)
        state_hash = hashlib.sha256(state.encode()).hexdigest()

        tx = AuthTransaction(
            state_hash=state_hash,
            nonce=nonce,
            code_verifier=verifier,
            created_at=now,
            expires_at=expires_at,
        )
        self.db.add(tx)
        self.db.commit()

        payload = {
            "state": state,
            "expires_at": int(expires_at.timestamp()),
        }
        params = {
            "response_type": "code",
            "client_id": self.settings.auth0_client_id,
            "redirect_uri": self.settings.auth0_redirect_uri,
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        if self.settings.auth0_audience:
            params["audience"] = self.settings.auth0_audience
        from fastapi.responses import RedirectResponse

        response = RedirectResponse(f"{metadata['authorization_endpoint']}?{urlencode(params)}")
        response.set_cookie(
            self.settings.auth_state_cookie_name,
            self._seal_state(payload),
            max_age=self.settings.auth_state_ttl_seconds,
            httponly=True,
            secure=self.settings.environment.lower() == "production",
            samesite="lax",
            path="/auth",
        )
        return response

    def callback(self, code: str, state: str, state_cookie: str):
        if not state_cookie:
            raise AuthenticationError("invalid authentication state")
        payload = self._unseal_state(state_cookie)
        if not hmac.compare_digest(state, payload["state"]):
            raise AuthenticationError("invalid authentication state")

        now = datetime.now(timezone.utc)
        state_hash = hashlib.sha256(state.encode()).hexdigest()

        tx = self.db.execute(
            select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
        ).scalar_one_or_none()

        if tx is None:
            raise AuthenticationError("invalid authentication state")
        if tx.consumed_at is not None:
            raise AuthenticationError("authentication state already consumed")
        if _as_utc(tx.expires_at) <= now:
            raise AuthenticationError("authentication state expired")

        result = self.db.execute(
            update(AuthTransaction)
            .where(AuthTransaction.id == tx.id, AuthTransaction.consumed_at.is_(None))
            .values(consumed_at=now)
        )
        if result.rowcount == 0:
            raise AuthenticationError("authentication state already consumed")
        self.db.commit()

        metadata = self._metadata()
        try:
            token_response = httpx.post(
                metadata["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.settings.auth0_client_id,
                    "client_secret": self.settings.auth0_client_secret,
                    "code": code,
                    "redirect_uri": self.settings.auth0_redirect_uri,
                    "code_verifier": tx.code_verifier,
                },
                timeout=10,
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            id_token = token_data["id_token"]
            jwks = httpx.get(metadata["jwks_uri"], timeout=10).json()
            claims = jwt.decode(
                id_token,
                jwks,
                claims_options={
                    "iss": {"essential": True, "value": self.issuer},
                    "aud": {"essential": True, "value": self.settings.auth0_client_id},
                    "sub": {"essential": True},
                },
            )
            claims.validate()
            if not hmac.compare_digest(str(claims.get("nonce", "")), tx.nonce):
                raise ValueError
            if claims.get("email_verified") is not True:
                raise ValueError
            email = str(claims["email"])
            subject = str(claims["sub"])
        except Exception as error:
            raise AuthenticationError("OIDC callback validation failed") from error

        identity = self.db.execute(
            select(UserIdentity).where(
                UserIdentity.provider == "auth0",
                UserIdentity.issuer == self.issuer,
                UserIdentity.subject == subject,
            )
        ).scalar_one_or_none()
        if identity is not None:
            user = identity.user
        else:
            user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user is None:
                user = User(email=email, full_name=claims.get("name"))
                self.db.add(user)
                self.db.flush()
            if not user.is_active:
                raise AuthenticationError("user is inactive")
            self.db.add(
                UserIdentity(user_id=user.id, provider="auth0", issuer=self.issuer, subject=subject)
            )

        if not user.is_active:
            raise AuthenticationError("user is inactive")
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        self.db.add(
            AuthSession(
                user_id=user.id,
                session_hash=hashlib.sha256(token.encode()).hexdigest(),
                created_at=now,
                expires_at=now + timedelta(seconds=self.settings.auth_session_ttl_seconds),
                last_used_at=now,
            )
        )
        self.db.commit()
        return user, token

    def logout(self, token: str | None) -> None:
        if token:
            session_hash = hashlib.sha256(token.encode()).hexdigest()
            session = self.db.execute(
                select(AuthSession).where(AuthSession.session_hash == session_hash)
            ).scalar_one_or_none()
            if session is not None:
                session.revoked_at = datetime.now(timezone.utc)
                self.db.commit()
