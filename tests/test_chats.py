from fastapi.testclient import TestClient

import app.api.chats as chats_api
from app.integrations.supabase import SupabaseAPIError
from app.main import app


client = TestClient(app)
CHAT_ID = "22222222-2222-4222-8222-222222222222"


def test_list_chats(monkeypatch):
    expected = [{"id": CHAT_ID, "title": "Project summary"}]
    monkeypatch.setattr(chats_api, "list_user_chats", lambda *args: expected)

    response = client.get("/api/chats/")

    assert response.status_code == 200
    assert response.json() == {"chats": expected}


def test_missing_chat_tables_return_setup_instructions(monkeypatch):
    def missing_table(*args):
        raise SupabaseAPIError(404, "Table not found.")

    monkeypatch.setattr(chats_api, "list_user_chats", missing_table)

    response = client.get("/api/chats/")

    assert response.status_code == 503
    assert "updated supabase/schema.sql" in response.json()["detail"]


def test_create_chat(monkeypatch):
    expected = {"id": CHAT_ID, "title": "Project summary"}
    captured = {}

    def create(user_id, title, access_token):
        captured.update(user_id=user_id, title=title, access_token=access_token)
        return expected

    monkeypatch.setattr(chats_api, "create_chat_session", create)
    response = client.post(
        "/api/chats/",
        json={"title": "Project summary"},
    )

    assert response.status_code == 201
    assert response.json() == {"chat": expected}
    assert captured["title"] == "Project summary"


def test_get_chat_with_turns(monkeypatch):
    chat = {"id": CHAT_ID, "title": "Project summary"}
    turns = [{"question": "What is the project?", "answer": "A RAG service."}]
    monkeypatch.setattr(chats_api, "get_chat_session", lambda *args: chat)
    monkeypatch.setattr(chats_api, "list_chat_turns", lambda *args: turns)

    response = client.get(f"/api/chats/{CHAT_ID}")

    assert response.status_code == 200
    assert response.json() == {"chat": chat, "turns": turns}


def test_chat_is_scoped_to_authenticated_user(monkeypatch):
    monkeypatch.setattr(chats_api, "get_chat_session", lambda *args: None)

    response = client.get(f"/api/chats/{CHAT_ID}")

    assert response.status_code == 404


def test_delete_chat(monkeypatch):
    deleted = []
    monkeypatch.setattr(
        chats_api,
        "get_chat_session",
        lambda *args: {"id": CHAT_ID, "title": "Old chat"},
    )
    monkeypatch.setattr(
        chats_api,
        "delete_chat_session",
        lambda *args: deleted.append(args),
    )

    response = client.delete(f"/api/chats/{CHAT_ID}")

    assert response.status_code == 204
    assert deleted
