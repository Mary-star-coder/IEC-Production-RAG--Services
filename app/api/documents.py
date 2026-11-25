
# Standard libraries.
import hashlib
import json
import logging
import uuid
from pathlib import Path

# FastAPI components.
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response

# Document processing and vector database operations.
from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_documents
from app.ingestion.vector_store import add_chunks, delete_document

# Validation and configuration.
from app.guardrails import validate_upload
from app.config import UPLOAD_DIR

# Response schemas.
from app.schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
)


# ---------------------------------------------------------
# ROUTER AND LOGGING CONFIGURATION
# ---------------------------------------------------------

logger = logging.getLogger("production_rag.documents")

router = APIRouter(prefix="/api/documents", tags=["Documents"])

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = UPLOAD_DIR / "registry.json"


# ---------------------------------------------------------
# DOCUMENT REGISTRY OPERATIONS
# ---------------------------------------------------------

def read_registry():
    """Read document records from the JSON registry."""

    if not REGISTRY_FILE.exists():
        return []

    try:
        return json.loads(
            REGISTRY_FILE.read_text(encoding="utf-8")
        )

    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to read document registry.")

        raise HTTPException(
            status_code=500,
            detail="Document registry could not be read.",
        )


def save_registry(documents):
    """Persist document records to the JSON registry."""

    REGISTRY_FILE.write_text(
        json.dumps(documents, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------
# DOCUMENT UPLOAD ENDPOINT
# ---------------------------------------------------------

@router.post(
    "/upload",
    status_code=201,
    response_model=DocumentUploadResponse,
)
async def upload_document(file: UploadFile = File(...)):
    """Validate, process, and index an uploaded document."""

    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    # Reject unsupported extensions with HTTP 415.
    if not filename or not validate_upload(filename, 1):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format.",
        )

    # Read uploaded content asynchronously.
    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    # Enforce the configured 15 MB upload limit.
    if not validate_upload(filename, len(content)):
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 15 MB limit.",
        )

    # Calculate SHA-256 for duplicate detection.
    file_hash = hashlib.sha256(content).hexdigest()

    documents = read_registry()

    for document in documents:
        if document["file_hash"] == file_hash:
            raise HTTPException(
                status_code=409,
                detail="This document has already been uploaded.",
            )

    document_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{document_id}{extension}"

    try:
        # Save the original document.
        saved_path.write_bytes(content)

        # Extract text and create chunks.
        pages = load_document(str(saved_path))
        chunks = chunk_documents(pages)

        if not chunks:
            raise ValueError("No extractable text found in document.")

        # Store embeddings and metadata in ChromaDB.
        chunk_count = add_chunks(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
        )

        document_record = {
            "document_id": document_id,
            "filename": filename,
            "file_hash": file_hash,
            "file_size": len(content),
            "chunk_count": chunk_count,
            "file_type": extension,
        }

        documents.append(document_record)
        save_registry(documents)

        logger.info(
            "Document uploaded successfully: document_id=%s filename=%s chunks=%s",
            document_id,
            filename,
            chunk_count,
        )

        return {
            "message": "Document uploaded successfully.",
            **document_record,
        }

    except HTTPException:
        saved_path.unlink(missing_ok=True)
        raise

    except Exception:
        logger.exception(
            "Document processing failed: document_id=%s filename=%s",
            document_id,
            filename,
        )

        # Roll back partially stored vectors and uploaded file.
        try:
            delete_document(document_id)
        except Exception:
            logger.exception(
                "Vector rollback failed: document_id=%s",
                document_id,
            )

        saved_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Document processing failed. Please try again.",
        )


# ---------------------------------------------------------
# DOCUMENT LIST ENDPOINT
# ---------------------------------------------------------

@router.get("/", response_model=DocumentListResponse)
def list_documents():
    """Return all registered uploaded documents."""

    return {"documents": read_registry()}


# ---------------------------------------------------------
# DOCUMENT DELETE ENDPOINT
# ---------------------------------------------------------

@router.delete(
    "/{document_id}",
    status_code=204,
    response_class=Response,
)
def remove_document(document_id: str):
    """Delete a document, its vectors, and its registry record."""

    documents = read_registry()

    document = next(
        (
            item for item in documents
            if item["document_id"] == document_id
        ),
        None,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # Remove associated vectors.
    delete_document(document_id)

    # Remove the original uploaded file.
    extension = document["file_type"]
    saved_path = UPLOAD_DIR / f"{document_id}{extension}"
    saved_path.unlink(missing_ok=True)

    # Update the registry.
    updated_documents = [
        item for item in documents
        if item["document_id"] != document_id
    ]

    save_registry(updated_documents)

    logger.info(
        "Document deleted successfully: document_id=%s",
        document_id,
    )

    # HTTP 204 must not return a response body.
    return Response(status_code=204)
