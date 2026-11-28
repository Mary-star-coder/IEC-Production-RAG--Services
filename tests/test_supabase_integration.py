import httpx
import pytest

import app.integrations.supabase as supabase


def test_user_lookup_sends_user_token_and_publishable_key(monkeypatch):
    captured = {}
    monkeypatch.setattr(supabase, "SUPABASE_URL", "https://project.example")
    monkeypatch.setattr(supabase, "SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(
            200,
            json={"id": "user-uuid", "email": "person@example.com"},
        )

    monkeypatch.setattr(supabase.httpx, "request", fake_request)

    user = supabase.get_authenticated_user("user-access-token")

    assert user["id"] == "user-uuid"
    assert captured["url"] == "https://project.example/auth/v1/user"
    assert captured["headers"]["apikey"] == "publishable-test-key"
    assert captured["headers"]["Authorization"] == "Bearer user-access-token"


def test_supabase_auth_errors_keep_status(monkeypatch):
    monkeypatch.setattr(supabase, "SUPABASE_URL", "https://project.example")
    monkeypatch.setattr(supabase, "SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")
    monkeypatch.setattr(
        supabase.httpx,
        "request",
        lambda *args, **kwargs: httpx.Response(
            401,
            json={"message": "invalid token"},
        ),
    )

    with pytest.raises(supabase.SupabaseAPIError) as error:
        supabase.get_authenticated_user("invalid-access-token")

    assert error.value.status_code == 401


def test_supabase_rate_limit_preserves_retry_after(monkeypatch):
    monkeypatch.setattr(supabase, "SUPABASE_URL", "https://project.example")
    monkeypatch.setattr(supabase, "SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")
    monkeypatch.setattr(
        supabase.httpx,
        "request",
        lambda *args, **kwargs: httpx.Response(
            429,
            headers={"Retry-After": "60"},
            json={"message": "Too many requests"},
        ),
    )

    with pytest.raises(supabase.SupabaseAPIError) as error:
        supabase._request("POST", "/auth/v1/signup")

    assert error.value.status_code == 429
    assert error.value.retry_after == "60"


def test_question_cache_uses_authenticated_user_and_upserts(monkeypatch):
    captured = []
    monkeypatch.setattr(supabase, "SUPABASE_URL", "https://project.example")
    monkeypatch.setattr(supabase, "SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")

    def fake_request(method, url, **kwargs):
        captured.append((method, url, kwargs))
        if method == "GET":
            return httpx.Response(200, json=[{"response": {"answer": "saved"}}])
        return httpx.Response(204)

    monkeypatch.setattr(supabase.httpx, "request", fake_request)

    cached = supabase.get_cached_answer(
        "user-uuid",
        "a" * 64,
        5,
        "user-access-token",
    )
    supabase.save_cached_answer(
        "user-uuid",
        "a" * 64,
        5,
        {"answer": "saved"},
        "user-access-token",
    )

    assert cached == {"answer": "saved"}
    assert captured[0][1] == "https://project.example/rest/v1/question_cache"
    assert captured[0][2]["headers"]["Authorization"] == "Bearer user-access-token"
    assert captured[1][0] == "POST"
    assert captured[1][2]["params"]["on_conflict"] == "user_id,question_hash,top_k"
    assert captured[1][2]["json"]["response"] == {"answer": "saved"}


def test_signup_uses_submitted_email_if_supabase_omits_it(monkeypatch):
    monkeypatch.setattr(supabase, "SUPABASE_URL", "https://project.example")
    monkeypatch.setattr(supabase, "SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")
    monkeypatch.setattr(
        supabase,
        "_request",
        lambda *args, **kwargs: httpx.Response(
            200,
            json={
                "user": {"id": "user-uuid"},
                "access_token": None,
                "refresh_token": None,
            },
        ),
    )

    result = supabase.register_user("person@example.com", "valid-password")

    assert result["user_id"] == "user-uuid"
    assert result["email"] == "person@example.com"
    assert result["requires_email_confirmation"] is True


def test_password_reset_uses_configured_redirect(monkeypatch):
    captured = {}
    monkeypatch.setattr(supabase, "SUPABASE_URL", "https://project.example")
    monkeypatch.setattr(supabase, "SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")
    monkeypatch.setattr(
        supabase,
        "SUPABASE_PASSWORD_RESET_REDIRECT_URL",
        "http://localhost:5173/reset-password",
    )

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(200)

    monkeypatch.setattr(supabase.httpx, "request", fake_request)

    supabase.send_password_reset_email("person@example.com")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://project.example/auth/v1/recover"
    assert captured["params"] == {
        "redirect_to": "http://localhost:5173/reset-password",
    }
    assert captured["json"] == {"email": "person@example.com"}


def test_password_update_sends_recovery_access_token(monkeypatch):
    captured = {}
    monkeypatch.setattr(supabase, "SUPABASE_URL", "https://project.example")
    monkeypatch.setattr(supabase, "SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(200, json={"id": "user-uuid"})

    monkeypatch.setattr(supabase.httpx, "request", fake_request)

    supabase.update_user_password("recovery-access-token", "new-password")

    assert captured["method"] == "PUT"
    assert captured["url"] == "https://project.example/auth/v1/user"
    assert captured["headers"]["Authorization"] == "Bearer recovery-access-token"
    assert captured["json"] == {"password": "new-password"}
