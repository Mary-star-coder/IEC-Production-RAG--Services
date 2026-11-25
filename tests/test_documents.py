
import hashlib
import json

from fastapi.testclient import TestClient

from app.main import app
import app.api.documents as documents_api


# Create a test client for sending requests to document API endpoints.
client = TestClient(app)


def setup_test_storage(tmp_path, monkeypatch):
    """
    Configure isolated temporary storage for document API tests.

    Using a temporary directory prevents test uploads and registry data
    from modifying the application's actual upload storage.
    """
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    # Replace the application's storage paths with temporary test paths.
    monkeypatch.setattr(documents_api, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(
        documents_api,
        "REGISTRY_FILE",
        upload_dir / "registry.json"
    )


def test_list_documents_empty(tmp_path, monkeypatch):
    """Verify that the API returns an empty list when no documents exist."""
    setup_test_storage(tmp_path, monkeypatch)

    response = client.get("/api/documents/")

    # An empty document registry should return HTTP 200 and no documents.
    assert response.status_code == 200
    assert response.json() == {"documents": []}


def test_upload_unsupported_file():
    """Verify that files with unsupported extensions are rejected."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.exe", b"content")}
    )

    # Executable files are not part of the supported document formats.
    assert response.status_code == 400


def test_upload_empty_file():
    """Verify that an empty document cannot be uploaded."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", b"")}
    )

    # Empty files should be rejected because they contain no usable content.
    assert response.status_code == 400


def test_upload_duplicate_file(tmp_path, monkeypatch):
    """Verify that uploading an identical document returns HTTP 409."""
    setup_test_storage(tmp_path, monkeypatch)

    content = b"sample document"

    # Calculate the SHA-256 hash used by the application for duplicate detection.
    file_hash = hashlib.sha256(content).hexdigest()

    # Add an existing document hash to the temporary registry.
    # This simulates a document that has already been uploaded.
    documents_api.REGISTRY_FILE.write_text(
        json.dumps([{"file_hash": file_hash}]),
        encoding="utf-8",
    )

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample.txt", content)}
    )

    # The API should identify the duplicate and return HTTP 409 Conflict.
    assert response.status_code == 409


def test_delete_missing_document(tmp_path, monkeypatch):
    """Verify that deleting a non-existent document returns HTTP 404."""
    setup_test_storage(tmp_path, monkeypatch)

    response = client.delete("/api/documents/unknown-id")

    # A document that does not exist should not be deleted.
    assert response.status_code == 404


def test_upload_file_too_large():
    """Verify that files exceeding the configured size limit are rejected."""

    # Generate content slightly larger than the application's 15 MB limit.
    content = b"A" * (15 * 1024 * 1024 + 1)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("large.txt", content)}
    )

    # Oversized uploads should return HTTP 413 Payload Too Large.
    assert response.status_code == 413
