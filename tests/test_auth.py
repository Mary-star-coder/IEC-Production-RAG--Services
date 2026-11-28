from fastapi.testclient import TestClient

from app.main import app
import app.api.auth as auth_api
from app.integrations.supabase import SupabaseAPIError


client = TestClient(app)


def test_register_uses_supabase_session(monkeypatch):
    monkeypatch.setattr(
        auth_api,
        "supabase_register",
        lambda email, password: {
            "user_id": "user-uuid",
            "email": email,
            "access_token": "access",
            "refresh_token": "refresh",
            "requires_email_confirmation": False,
        },
    )

    response = client.post(
        "/api/auth/register",
        json={"email": "Person@Example.com", "password": "valid-password"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == "user-uuid"
    assert response.json()["access_token"] == "access"
    assert response.json()["refresh_token"] == "refresh"


def test_register_can_require_email_confirmation(monkeypatch):
    monkeypatch.setattr(
        auth_api,
        "supabase_register",
        lambda email, password: {
            "user_id": "user-uuid",
            "email": email,
            "access_token": None,
            "refresh_token": None,
            "requires_email_confirmation": True,
        },
    )

    response = client.post(
        "/api/auth/register",
        json={"email": "person@example.com", "password": "valid-password"},
    )

    assert response.status_code == 201
    assert response.json()["requires_email_confirmation"] is True
    assert response.json()["access_token"] is None


def test_register_reports_supabase_rate_limit(monkeypatch):
    def rate_limited_register(email, password):
        raise SupabaseAPIError(
            429,
            "Too many requests",
            retry_after="60",
        )

    monkeypatch.setattr(auth_api, "supabase_register", rate_limited_register)

    response = client.post(
        "/api/auth/register",
        json={"email": "person@example.com", "password": "valid-password"},
    )

    assert response.status_code == 429
    assert "Too many registration attempts" in response.json()["detail"]
    assert response.headers["retry-after"] == "60"


def test_password_reset_returns_enumeration_safe_message(monkeypatch):
    sent_to = []
    monkeypatch.setattr(
        auth_api,
        "send_password_reset_email",
        lambda email: sent_to.append(email),
    )

    response = client.post(
        "/api/auth/password-reset",
        json={"email": "Person@Example.com"},
    )

    assert response.status_code == 200
    assert sent_to == ["person@example.com"]
    assert "If an account exists" in response.json()["message"]


def test_password_update_uses_authenticated_recovery_token(monkeypatch):
    updated = []
    monkeypatch.setattr(
        auth_api,
        "supabase_update_password",
        lambda token, password: updated.append((token, password)),
    )

    response = client.put(
        "/api/auth/password",
        headers={"Authorization": "Bearer recovery-token"},
        json={"password": "new-valid-password"},
    )

    assert response.status_code == 200
    assert updated == [("test-access-token", "new-valid-password")]
    assert "Password updated" in response.json()["message"]


def test_password_update_rejects_expired_recovery_token(monkeypatch):
    def reject_password_update(token, password):
        raise SupabaseAPIError(401, "Invalid token")

    monkeypatch.setattr(
        auth_api,
        "supabase_update_password",
        reject_password_update,
    )

    response = client.put(
        "/api/auth/password",
        headers={"Authorization": "Bearer recovery-token"},
        json={"password": "new-valid-password"},
    )

    assert response.status_code == 401
    assert "invalid or expired" in response.json()["detail"]


def test_login_returns_refresh_token(monkeypatch):
    monkeypatch.setattr(
        auth_api,
        "supabase_login",
        lambda email, password: {
            "user_id": "user-uuid",
            "email": email,
            "access_token": "access",
            "refresh_token": "refresh",
            "requires_email_confirmation": False,
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "person@example.com", "password": "valid-password"},
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] == "refresh"


def test_login_reports_unconfirmed_email(monkeypatch):
    def reject_unconfirmed_user(email, password):
        raise SupabaseAPIError(400, "Email not confirmed")

    monkeypatch.setattr(auth_api, "supabase_login", reject_unconfirmed_user)

    response = client.post(
        "/api/auth/login",
        json={"email": "person@example.com", "password": "valid-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Confirm your email before signing in."


def test_refresh_rotates_session(monkeypatch):
    monkeypatch.setattr(
        auth_api,
        "refresh_user_session",
        lambda refresh_token: {
            "user_id": "user-uuid",
            "email": "person@example.com",
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "requires_email_confirmation": False,
        },
    )

    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "old-refresh"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access"
    assert response.json()["refresh_token"] == "new-refresh"
