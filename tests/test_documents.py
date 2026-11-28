import hashlib

from fastapi.testclient import TestClient

from app.exceptions import RateLimitExceededError
from app.main import app
import app.api.documents as documents_api


client = TestClient(app)


def setup_test_storage(monkeypatch):
    """Mock Supabase document operations so tests never call cloud services."""
    monkeypatch.setattr(documents_api, "list_user_documents", lambda *args: [])
    monkeypatch.setattr(documents_api, "find_duplicate_document", lambda *args: False)
    monkeypatch.setattr(documents_api, "get_user_document", lambda *args: None)
    monkeypatch.setattr(documents_api, "document_exists", lambda *args: False)


def test_list_documents_empty(monkeypatch):
    setup_test_storage(monkeypatch)

    response = client.get("/api/documents/")

    assert response.status_code == 200
    assert response.json() == {"documents": []}


def test_upload_unsupported_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.exe", b"content")},
    )

    assert response.status_code == 415


def test_upload_empty_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", b"")},
    )

    assert response.status_code == 400


def test_upload_duplicate_file(monkeypatch):
    setup_test_storage(monkeypatch)
    content = b"sample document"
    expected_hash = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(
        documents_api,
        "find_duplicate_document",
        lambda user_id, file_hash, token: file_hash == expected_hash,
    )

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.txt", content)},
    )

    assert response.status_code == 409


def test_upload_qdrant_duplicate_skips_document_parsing(monkeypatch):
    setup_test_storage(monkeypatch)
    monkeypatch.setattr(documents_api, "document_exists", lambda *args: True)
    parsed = []
    monkeypatch.setattr(
        documents_api,
        "load_document",
        lambda path: parsed.append(path),
    )

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.txt", b"sample document")},
    )

    assert response.status_code == 409
    assert parsed == []


def test_delete_missing_document(monkeypatch):
    setup_test_storage(monkeypatch)

    response = client.delete("/api/documents/unknown-id")

    assert response.status_code == 404


def test_upload_file_too_large():
    content = b"A" * (15 * 1024 * 1024 + 1)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("large.txt", content)},
    )

    assert response.status_code == 413


def test_upload_persists_document_in_supabase_and_qdrant(monkeypatch):
    setup_test_storage(monkeypatch)
    monkeypatch.setattr(
        documents_api,
        "load_document",
        lambda path: [{"page": 1, "text": "A test document body."}],
    )
    monkeypatch.setattr(
        documents_api,
        "chunk_documents",
        lambda pages: [{"page": 1, "position": 0, "text": pages[0]["text"]}],
    )
    indexed = []
    monkeypatch.setattr(
        documents_api,
        "add_chunks",
        lambda **kwargs: indexed.append(kwargs) or 1,
    )
    uploaded = []
    monkeypatch.setattr(
        documents_api,
        "upload_document_object",
        lambda path, content, content_type, token: uploaded.append(path),
    )
    monkeypatch.setattr(
        documents_api,
        "create_document_record",
        lambda record, token: record,
    )

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.txt", b"A test document body.")},
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "sample.txt"
    assert len(uploaded) == 1
    assert uploaded[0].startswith("1/")
    assert indexed[0]["file_hash"] == response.json()["file_hash"]


def test_upload_embedding_rate_limit_returns_retry_after_and_rolls_back(monkeypatch):
    setup_test_storage(monkeypatch)
    monkeypatch.setattr(
        documents_api,
        "load_document",
        lambda path: [{"page": 1, "text": "A test document body."}],
    )
    monkeypatch.setattr(
        documents_api,
        "chunk_documents",
        lambda pages: [{"page": 1, "position": 0, "text": pages[0]["text"]}],
    )
    monkeypatch.setattr(
        documents_api,
        "upload_document_object",
        lambda *args: None,
    )
    def rate_limited_add_chunks(**kwargs):
        raise RateLimitExceededError(
            "Embedding quota reached.",
            retry_after=59,
        )

    monkeypatch.setattr(documents_api, "add_chunks", rate_limited_add_chunks)
    deleted_vectors = []
    deleted_objects = []
    monkeypatch.setattr(
        documents_api,
        "delete_document",
        lambda *args, **kwargs: deleted_vectors.append(args),
    )
    monkeypatch.setattr(
        documents_api,
        "delete_document_object",
        lambda *args: deleted_objects.append(args),
    )

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.txt", b"A test document body.")},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "59"
    assert response.json()["detail"] == "Embedding quota reached."
    assert deleted_vectors
    assert deleted_objects
