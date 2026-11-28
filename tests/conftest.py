import os

os.environ["ENVIRONMENT"] = "test"
os.environ["QDRANT_URL"] = ""
os.environ["QDRANT_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_PUBLISHABLE_KEY"] = ""
os.environ["VITE_SUPABASE_URL"] = ""
os.environ["VITE_SUPABASE_PUBLISHABLE_KEY"] = ""

import pytest

from app.main import app
from app.auth.dependencies import get_current_user
import app.ingestion.vector_store as vector_store
import app.api.questions as questions_api


@pytest.fixture(autouse=True)
def authenticated_test_user(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "email": "test@example.com",
        "access_token": "test-access-token",
    }
    monkeypatch.setattr(
        vector_store,
        "embed_texts",
        lambda texts, task_type="RETRIEVAL_DOCUMENT": [
            [1.0] + [0.0] * 3071 for _ in texts
        ],
    )
    monkeypatch.setattr(questions_api, "get_cached_answer", lambda *args: None)
    monkeypatch.setattr(questions_api, "save_cached_answer", lambda *args: None)

    yield

    app.dependency_overrides.pop(get_current_user, None)
