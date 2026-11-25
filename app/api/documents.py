
# ---------------------------------------------------------
# STANDARD LIBRARY IMPORTS
# ---------------------------------------------------------

import hashlib
import json
import logging
import uuid

from pathlib import Path
from typing import Any


# ---------------------------------------------------------
# FASTAPI IMPORTS
# ---------------------------------------------------------

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
)

from fastapi.responses import Response


# ---------------------------------------------------------
# PROJECT IMPORTS
# ---------------------------------------------------------

from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_documents

from app.ingestion.vector_store import (
    add_chunks,
    delete_document,
)

from app.exceptions import ServiceUnavailableError

from app.guardrails import validate_upload
from app.config import UPLOAD_DIR

from app.schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
)

from app.auth.dependencies import get_current_user


# ---------------------------------------------------------
# ROUTER AND LOGGING CONFIGURATION
# ---------------------------------------------------------

logger = logging.getLogger("production_rag.documents")

router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = UPLOAD_DIR / "registry.json"


# ---------------------------------------------------------
# DOCUMENT REGISTRY OPERATIONS
# ---------------------------------------------------------

def read_registry() -> list[dict[str, Any]]:
    """
    Read registered document records from the JSON file.
    """

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


def save_registry(documents: list[dict[str, Any]]) -> None:
    """
    Save document records to the JSON registry.
    """

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
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Upload and index a document for the authenticated user.
    """

    user_id = str(current_user["user_id"])

    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or not validate_upload(filename, 1):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    if not validate_upload(filename, len(content)):
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 15 MB limit.",
        )

    file_hash = hashlib.sha256(content).hexdigest()

    documents = read_registry()

    # Duplicate detection is restricted to this user.
    for document in documents:
        if (
            document.get("owner_user_id") == user_id
            and document["file_hash"] == file_hash
        ):
            raise HTTPException(
                status_code=409,
                detail="This document has already been uploaded.",
            )

    document_id = str(uuid.uuid4())

    saved_path = UPLOAD_DIR / f"{document_id}{extension}"

    try:
        saved_path.write_bytes(content)

        pages = load_document(str(saved_path))

        chunks = chunk_documents(pages)

        if not chunks:
            raise ValueError(
                "No extractable text found in document."
            )

        # Store vectors with the authenticated user's ID.
        chunk_count = add_chunks(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            user_id=user_id,
        )

        document_record = {
            "document_id": document_id,
            "filename": filename,
            "file_hash": file_hash,
            "file_size": len(content),
            "chunk_count": chunk_count,
            "file_type": extension,
            "owner_user_id": user_id,
        }

        documents.append(document_record)

        save_registry(documents)

        logger.info(
            "Document uploaded: document_id=%s user_id=%s chunks=%s",
            document_id,
            user_id,
            chunk_count,
        )

        # Do not expose internal ownership metadata in the response.
        response_record = {
            key: value
            for key, value in document_record.items()
            if key != "owner_user_id"
        }

        return {
            "message": "Document uploaded successfully.",
            **response_record,
        }

    except HTTPException:
        saved_path.unlink(missing_ok=True)
        raise

    except ServiceUnavailableError:
        logger.exception(
            "Vector database unavailable during upload: document_id=%s",
            document_id,
        )

        try:
            delete_document(
                document_id,
                user_id=user_id,
            )

        except ServiceUnavailableError:
            logger.exception(
                "Vector rollback failed: document_id=%s",
                document_id,
            )

        saved_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=503,
            detail=(
                "Document service is temporarily unavailable. "
                "Please try again."
            ),
        )

    except Exception:
        logger.exception(
            "Document processing failed: document_id=%s filename=%s",
            document_id,
            filename,
        )

        try:
            delete_document(
                document_id,
                user_id=user_id,
            )

        except ServiceUnavailableError:
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

@router.get(
    "/",
    response_model=DocumentListResponse,
)
def list_documents(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Return only documents owned by the authenticated user.
    """

    user_id = str(current_user["user_id"])

    documents = read_registry()

    user_documents = [
        document
        for document in documents
        if document.get("owner_user_id") == user_id
    ]

    # Hide internal ownership metadata.
    response_documents = [
        {
            key: value
            for key, value in document.items()
            if key != "owner_user_id"
        }
        for document in user_documents
    ]

    return {
        "documents": response_documents
    }


# ---------------------------------------------------------
# DOCUMENT DELETE ENDPOINT
# ---------------------------------------------------------

@router.delete(
    "/{document_id}",
    status_code=204,
    response_class=Response,
)
def remove_document(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Delete a document only if it belongs to the authenticated user.
    """

    user_id = str(current_user["user_id"])

    documents = read_registry()

    # Find a document belonging to this user only.
    document = next(
        (
            item
            for item in documents
            if (
                item["document_id"] == document_id
                and item.get("owner_user_id") == user_id
            )
        ),
        None,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # Delete only this user's vectors.
    try:
        delete_document(
            document_id,
            user_id=user_id,
        )

    except ServiceUnavailableError:
        logger.exception(
            "Vector database unavailable during deletion: document_id=%s",
            document_id,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Document service is temporarily unavailable. "
                "Please try again."
            ),
        )

    extension = document["file_type"]

    saved_path = UPLOAD_DIR / f"{document_id}{extension}"

    saved_path.unlink(missing_ok=True)

    updated_documents = [
        item
        for item in documents
        if item["document_id"] != document_id
    ]

    save_registry(updated_documents)

    logger.info(
        "Document deleted: document_id=%s user_id=%s",
        document_id,
        user_id,
    )

    return Response(status_code=204)
