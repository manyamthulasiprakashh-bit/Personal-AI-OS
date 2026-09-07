from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from authlib.jose import JsonWebKey, jwt
from fastapi import HTTPException
from sqlalchemy import select

from app.api import dependencies
from app.api.dependencies import CurrentUser, get_current_user
from app.config import Settings
from app.database.session import SessionLocal
from app.models.auth import AuthSession, AuthTransaction
from app.models.user import User
from app.services.auth_service import AuthService, AuthenticationError, _as_utc


class _FakeOidcProvider:
    """Fully offline OIDC fake: discovery + JWKS + token endpoint.

    Patches ``app.services.auth_service.httpx.get`` and ``.post`` for every
    test in this module (autouse fixture below), so no code path in
    ``AuthService`` can reach the real network regardless of test ordering.
    """

    def __init__(self, issuer: str = "https://test.auth0.com", client_id: str = "test-client-id"):
        self.issuer = issuer
        self.client_id = client_id
        self._key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        self._jwk_dict = self._key.as_dict(is_private=False)
        self.posted_data: dict = {}
        # Tests may mutate this dict before calling service.callback(...) to
        # exercise nonce/issuer/audience mismatch, expiry, email_verified,
        # subject, and any other claim-level scenario.
        self.claims: dict = {}

    def get(self, url, **kwargs):
        if url.endswith("/.well-known/openid-configuration"):
            return SimpleNamespace(
                status_code=200,
                raise_for_status=lambda: None,
                json=lambda: {
                    "issuer": self.issuer,
                    "authorization_endpoint": f"{self.issuer}/authorize",
                    "token_endpoint": f"{self.issuer}/oauth/token",
                    "jwks_uri": f"{self.issuer}/.well-known/jwks.json",
                },
            )
        if url.endswith("/.well-known/jwks.json"):
            return SimpleNamespace(
                status_code=200,
                raise_for_status=lambda: None,
                json=lambda: {"keys": [self._jwk_dict]},
            )
        raise ValueError(f"Unexpected GET URL: {url}")

    def post(self, url, **kwargs):
        if url.endswith("/oauth/token"):
            data = kwargs.get("data", {})
            self.posted_data.update(data)

            header = {"alg": "RS256", "kid": self._jwk_dict.get("kid", "test-key")}
            claims = {
                "iss": self.issuer,
                "aud": self.client_id,
                "sub": f"auth0|test-{uuid4()}",
                "email": f"user-{uuid4()}@example.com",
                "email_verified": True,
                "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
                "iat": int(datetime.now(timezone.utc).timestamp()),
            }
            claims.update(self.claims)
            id_token = jwt.encode(header, claims, self._key).decode("ascii")
            return SimpleNamespace(
                status_code=200,
                raise_for_status=lambda: None,
                json=lambda: {"id_token": id_token, "access_token": "acc-123"},
            )
        raise ValueError(f"Unexpected POST URL: {url}")


@pytest.fixture(autouse=True)
def fake_oidc(monkeypatch):
    """Autouse: every test in this module gets a fully offline OIDC provider.

    Returns the provider so tests can mutate ``fake_oidc.claims`` or inspect
    ``fake_oidc.posted_data``.
    """
    provider = _FakeOidcProvider()
    monkeypatch.setattr("app.services.auth_service.httpx.get", provider.get)
    monkeypatch.setattr("app.services.auth_service.httpx.post", provider.post)
    return provider


def test_current_user_rejects_development_identity_in_production(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(
            environment="production", development_user_email="user@example.com"
        ),
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(SessionLocal())

    assert error.value.status_code == 401


def test_current_user_resolves_valid_server_session(monkeypatch):
    db = SessionLocal()
    user = User(email=f"auth-{uuid4()}@example.com")
    token = "opaque-session-token"
    now = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(
        AuthSession(
            user_id=user.id,
            session_hash=hashlib.sha256(token.encode()).hexdigest(),
            created_at=now,
            expires_at=now + timedelta(hours=1),
            last_used_at=now,
        )
    )
    db.commit()
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(
            environment="production", auth_session_cookie_name="personal_ai_os_session"
        ),
    )

    class Request:
        cookies = {"personal_ai_os_session": token}

    try:
        resolved = dependencies.resolve_current_user(Request(), db)
    finally:
        db.close()

    assert resolved == CurrentUser(user.id, user.email)


@pytest.mark.parametrize("revoked", [True, False])
def test_current_user_rejects_expired_or_revoked_session(revoked, monkeypatch):
    db = SessionLocal()
    user = User(email=f"auth-expired-{uuid4()}@example.com")
    token = "expired-session-token"
    now = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(
        AuthSession(
            user_id=user.id,
            session_hash=hashlib.sha256(token.encode()).hexdigest(),
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(minutes=1),
            last_used_at=now - timedelta(hours=1),
            revoked_at=now if revoked else None,
        )
    )
    db.commit()
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(
            environment="production", auth_session_cookie_name="personal_ai_os_session"
        ),
    )

    class Request:
        cookies = {"personal_ai_os_session": token}

    try:
        with pytest.raises(HTTPException) as error:
            dependencies.resolve_current_user(Request(), db)
    finally:
        db.close()

    assert error.value.status_code == 401


def test_logout_revokes_session_and_does_not_store_plaintext():
    db = SessionLocal()
    user = User(email=f"auth-logout-{uuid4()}@example.com")
    token = "logout-session-token"
    now = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)

    session = AuthSession(
        user_id=user.id,
        session_hash=hashlib.sha256(token.encode()).hexdigest(),
        created_at=now,
        expires_at=now + timedelta(hours=1),
        last_used_at=now,
    )
    db.add(session)
    db.commit()

    AuthService(db, Settings(environment="test")).logout(token)
    db.refresh(session)
    db.close()

    assert session.session_hash != token
    assert session.revoked_at is not None


def test_oidc_state_rejects_tampered_payload():
    service = AuthService(SessionLocal(), Settings(environment="production", auth_mode="oidc"))
    sealed = service._seal_state(
        {"state": "a", "nonce": "b", "verifier": "c", "expires_at": 4102444800}
    )

    with pytest.raises(AuthenticationError):
        service._unseal_state(sealed + "tampered")


def test_as_utc_preserves_instant_for_aware_datetime():
    aware = datetime(2026, 9, 7, 12, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    normalized = _as_utc(aware)

    assert normalized.tzinfo is timezone.utc
    assert normalized == aware
    assert normalized.timestamp() == aware.timestamp()


def test_as_utc_interprets_naive_datetime_as_utc():
    naive = datetime(2026, 9, 7, 12, 30, 0)
    normalized = _as_utc(naive)

    assert normalized.tzinfo is timezone.utc
    assert normalized.replace(tzinfo=None) == naive
    assert normalized.timestamp() == naive.replace(tzinfo=timezone.utc).timestamp()


def test_as_utc_is_idempotent_on_utc_aware_datetime():
    aware = datetime(2026, 9, 7, 12, 30, 0, tzinfo=timezone.utc)

    assert _as_utc(aware) is aware or _as_utc(aware) == aware
    assert _as_utc(aware).tzinfo is timezone.utc


def test_login_creates_server_side_auth_transaction(fake_oidc):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    url = response.headers["location"]
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    state = qs["state"][0]
    nonce = qs["nonce"][0]

    state_hash = hashlib.sha256(state.encode()).hexdigest()
    tx = db.execute(
        select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
    ).scalar_one_or_none()

    assert tx is not None
    assert tx.nonce == nonce
    assert tx.consumed_at is None
    assert _as_utc(tx.expires_at) > datetime.now(timezone.utc)
    db.close()


def test_successful_callback_consumes_transaction(fake_oidc):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    state_hash = hashlib.sha256(state.encode()).hexdigest()
    tx = db.execute(
        select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
    ).scalar_one()

    fake_oidc.claims.update({"nonce": tx.nonce, "email": "callback-user@example.com"})

    user, token = service.callback("code123", state, cookie)
    db.refresh(tx)

    assert user.email == "callback-user@example.com"
    assert token is not None
    assert tx.consumed_at is not None
    db.close()


def test_second_callback_using_identical_state_fails(fake_oidc):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    state_hash = hashlib.sha256(state.encode()).hexdigest()
    tx = db.execute(
        select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
    ).scalar_one()

    fake_oidc.claims.update({"nonce": tx.nonce, "email": "replay-user@example.com"})

    # First callback succeeds
    service.callback("code123", state, cookie)

    # Second callback with same state fails
    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", state, cookie)

    assert "already consumed" in str(exc_info.value)
    db.close()


def test_callback_with_consumed_transaction_fails(monkeypatch):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    state = "state-consumed-test"
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    tx = AuthTransaction(
        state_hash=state_hash,
        nonce="nonce-consumed",
        code_verifier="verifier-consumed",
        created_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=5),
        consumed_at=now - timedelta(seconds=10),
    )
    db.add(tx)
    db.commit()

    cookie = service._seal_state(
        {"state": state, "expires_at": int((now + timedelta(minutes=5)).timestamp())}
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", state, cookie)

    assert "already consumed" in str(exc_info.value)
    db.close()


def test_callback_with_expired_transaction_fails(monkeypatch):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    state = "state-expired-test"
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    tx = AuthTransaction(
        state_hash=state_hash,
        nonce="nonce-expired",
        code_verifier="verifier-expired",
        created_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(seconds=1),
        consumed_at=None,
    )
    db.add(tx)
    db.commit()

    cookie = service._seal_state(
        {"state": state, "expires_at": int((now + timedelta(minutes=5)).timestamp())}
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", state, cookie)

    assert "expired" in str(exc_info.value)
    db.close()


def test_callback_rejects_expired_transaction_with_naive_reloaded_timestamp(fake_oidc):
    """Simulates SQLite reloading a DateTime(timezone=True) column as naive.

    The production comparison at auth_service.py ``_as_utc(tx.expires_at) <= now``
    must treat the naive value as UTC and still reject the expired transaction.
    """
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    state = "state-naive-expired-test"
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    tx = AuthTransaction(
        state_hash=state_hash,
        nonce="nonce-naive-expired",
        code_verifier="verifier-naive-expired",
        created_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(seconds=1),
        consumed_at=None,
    )
    db.add(tx)
    db.commit()

    # Force a fresh read from SQLite, which returns naive datetimes for
    # DateTime(timezone=True) columns.
    db.expire_all()
    reloaded = db.execute(
        select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
    ).scalar_one()
    assert reloaded.expires_at.tzinfo is None  # confirms the SQLite behavior

    cookie = service._seal_state(
        {"state": state, "expires_at": int((now + timedelta(minutes=5)).timestamp())}
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", state, cookie)

    assert "expired" in str(exc_info.value)
    db.close()


def test_callback_accepts_valid_transaction_with_naive_reloaded_timestamp(fake_oidc):
    """Companion to the expired case: a *valid* transaction whose expires_at
    reloads as naive from SQLite must still be accepted (no TypeError)."""
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    state_hash = hashlib.sha256(state.encode()).hexdigest()
    db.expire_all()  # force SQLite reload -> naive datetimes
    tx = db.execute(
        select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
    ).scalar_one()
    assert tx.expires_at.tzinfo is None

    fake_oidc.claims.update({"nonce": tx.nonce, "email": "naive-valid@example.com"})

    user, token = service.callback("code123", state, cookie)
    assert user.email == "naive-valid@example.com"
    assert token is not None
    db.close()


def test_callback_with_mismatched_state_fails(monkeypatch):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", "wrong-state", cookie)

    assert "invalid authentication state" in str(exc_info.value)
    db.close()


def test_callback_with_missing_state_fails(monkeypatch):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)

    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", "", "")

    assert "invalid authentication state" in str(exc_info.value)
    db.close()


def test_callback_with_mismatched_nonce_fails(fake_oidc):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    fake_oidc.claims.update({"nonce": "wrong-nonce", "email": "wrong-nonce@example.com"})

    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", state, cookie)

    assert "OIDC callback validation failed" in str(exc_info.value)
    db.close()


def test_callback_with_missing_nonce_fails(fake_oidc):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    fake_oidc.claims.update({"nonce": "", "email": "missing-nonce@example.com"})

    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", state, cookie)

    assert "OIDC callback validation failed" in str(exc_info.value)
    db.close()


def test_callback_cannot_replace_pkce_verifier(fake_oidc):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    state_hash = hashlib.sha256(state.encode()).hexdigest()
    tx = db.execute(
        select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
    ).scalar_one()

    fake_oidc.claims.update({"nonce": tx.nonce, "email": "pkce-test@example.com"})

    service.callback("code123", state, cookie)

    assert fake_oidc.posted_data["code_verifier"] == tx.code_verifier
    db.close()


def test_concurrent_repeated_callback_cannot_create_two_application_sessions(fake_oidc):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    state_hash = hashlib.sha256(state.encode()).hexdigest()
    tx = db.execute(
        select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
    ).scalar_one()

    fake_oidc.claims.update({"nonce": tx.nonce, "email": "single-session@example.com"})

    user, token = service.callback("code123", state, cookie)

    with pytest.raises(AuthenticationError):
        service.callback("code123", state, cookie)

    sessions = db.execute(select(AuthSession).where(AuthSession.user_id == user.id)).scalars().all()
    assert len(sessions) == 1
    db.close()


def test_consumed_transaction_cannot_be_reused_after_browser_cookie_deletion(fake_oidc):
    db = SessionLocal()
    settings = Settings(
        environment="test",
        auth_mode="oidc",
        auth0_issuer="https://test.auth0.com",
        auth0_client_id="test-client-id",
        auth0_client_secret="test-client-secret",
    )
    service = AuthService(db, settings)
    response = service.login_redirect()

    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]

    state_hash = hashlib.sha256(state.encode()).hexdigest()
    tx = db.execute(
        select(AuthTransaction).where(AuthTransaction.state_hash == state_hash)
    ).scalar_one()

    fake_oidc.claims.update({"nonce": tx.nonce, "email": "cookie-del@example.com"})

    # First callback succeeds
    service.callback("code123", state, cookie)

    # Browser deletes cookie in response, but attacker creates a new valid signed cookie for that state
    new_cookie = service._seal_state(
        {"state": state, "expires_at": int(_as_utc(tx.expires_at).timestamp())}
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.callback("code123", state, new_cookie)

    assert "already consumed" in str(exc_info.value)
    db.close()
