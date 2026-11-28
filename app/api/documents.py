import hashlib
import logging
import mimetypes
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.auth.dependencies import get_current_user
from app.exceptions import RateLimitExceededError, ServiceUnavailableError
from app.guardrails import validate_upload
from app.ingestion.chunker import chunk_documents
from app.ingestion.loader import load_document
from app.ingestion.vector_store import (
    add_chunks,
    delete_document,
    document_exists,
)
from app.integrations.supabase import (
    SupabaseAPIError,
    SupabaseUnavailableError,
    create_document_record,
    delete_document_object,
    delete_document_record,
    find_duplicate_document,
    get_user_document,
    list_user_documents,
    upload_document_object,
)
from app.schemas import DocumentListResponse, DocumentUploadResponse


logger = logging.getLogger("production_rag.documents")
router = APIRouter(prefix="/api/documents", tags=["Documents"])

MAX_UPLOAD_SIZE = 15 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024


def _service_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Document service is temporarily unavailable. Please try again.",
    )


def _rollback_upload(
    document_id: str,
    user_id: str,
    object_path: str,
    access_token: str,
    *,
    vector_write_attempted: bool,
    object_uploaded: bool,
) -> None:
    if vector_write_attempted:
        try:
            delete_document(document_id, user_id=user_id)
        except ServiceUnavailableError:
            logger.exception(
                "Vector rollback failed: document_id=%s",
                document_id,
            )
    if object_uploaded:
        try:
            delete_document_object(object_path, access_token)
        except (SupabaseAPIError, SupabaseUnavailableError):
            logger.exception(
                "Storage rollback failed: document_id=%s",
                document_id,
            )


@router.post(
    "/upload",
    status_code=201,
    response_model=DocumentUploadResponse,
)
def upload_document(
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Parse, index, and persist a user's document."""

    user_id = str(current_user["user_id"])
    access_token = str(current_user["access_token"])
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or not validate_upload(filename, 1):
        file.file.close()
        raise HTTPException(status_code=415, detail="Unsupported file format.")

    content_buffer = bytearray()
    try:
        while True:
            chunk = file.file.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            content_buffer.extend(chunk)
            if len(content_buffer) > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="File exceeds the 15 MB limit.",
                )
    finally:
        file.file.close()

    if not content_buffer:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    content = bytes(content_buffer)
    if not validate_upload(filename, len(content)):
        raise HTTPException(status_code=413, detail="File exceeds the 15 MB limit.")

    file_hash = hashlib.sha256(content).hexdigest()
    try:
        if find_duplicate_document(user_id, file_hash, access_token):
            raise HTTPException(
                status_code=409,
                detail="This document has already been uploaded.",
            )
    except SupabaseAPIError as exc:
        logger.error("Supabase duplicate lookup failed: status=%s", exc.status_code)
        raise _service_unavailable() from exc
    except SupabaseUnavailableError as exc:
        logger.error("Supabase duplicate lookup could not reach the service.")
        raise _service_unavailable() from exc

    try:
        if document_exists(file_hash, user_id):
            raise HTTPException(
                status_code=409,
                detail="This document has already been uploaded.",
            )
    except ServiceUnavailableError as exc:
        logger.error("Qdrant duplicate lookup failed.")
        raise _service_unavailable() from exc

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)

        pages = load_document(str(temporary_path))
        chunks = chunk_documents(pages)
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No extractable text found in document.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Document parsing failed: filename=%s", filename)
        raise HTTPException(
            status_code=400,
            detail="The uploaded document could not be parsed.",
        ) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    document_id = str(uuid.uuid4())
    object_path = f"{user_id}/{document_id}{extension}"
    vector_write_attempted = False
    object_uploaded = False
    try:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        upload_document_object(
            object_path,
            content,
            content_type,
            access_token,
        )
        object_uploaded = True

        vector_write_attempted = True
        chunk_count = add_chunks(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            user_id=user_id,
            file_hash=file_hash,
        )
        if chunk_count < 1:
            raise ValueError("Document indexing produced no chunks.")

        record = {
            "document_id": document_id,
            "owner_user_id": user_id,
            "filename": filename,
            "file_hash": file_hash,
            "file_size": len(content),
            "chunk_count": chunk_count,
            "file_type": extension,
        }
        saved_record = create_document_record(record, access_token)
    except HTTPException:
        _rollback_upload(
            document_id,
            user_id,
            object_path,
            access_token,
            vector_write_attempted=vector_write_attempted,
            object_uploaded=object_uploaded,
        )
        raise
    except SupabaseAPIError as exc:
        _rollback_upload(
            document_id,
            user_id,
            object_path,
            access_token,
            vector_write_attempted=vector_write_attempted,
            object_uploaded=object_uploaded,
        )
        if exc.status_code == 409:
            raise HTTPException(
                status_code=409,
                detail="This document has already been uploaded.",
            ) from exc
        logger.error("Supabase document persistence failed: status=%s", exc.status_code)
        raise _service_unavailable() from exc
    except RateLimitExceededError as exc:
        _rollback_upload(
            document_id,
            user_id,
            object_path,
            access_token,
            vector_write_attempted=vector_write_attempted,
            object_uploaded=object_uploaded,
        )
        logger.warning(
            "Document upload rate-limited by the embedding service."
        )
        headers = (
            {"Retry-After": str(exc.retry_after)}
            if exc.retry_after is not None
            else None
        )
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers=headers,
        ) from exc
    except (SupabaseUnavailableError, ServiceUnavailableError) as exc:
        _rollback_upload(
            document_id,
            user_id,
            object_path,
            access_token,
            vector_write_attempted=vector_write_attempted,
            object_uploaded=object_uploaded,
        )
        logger.error("Document service dependency unavailable.")
        raise _service_unavailable() from exc
    except Exception as exc:
        _rollback_upload(
            document_id,
            user_id,
            object_path,
            access_token,
            vector_write_attempted=vector_write_attempted,
            object_uploaded=object_uploaded,
        )
        logger.exception("Document indexing failed: document_id=%s", document_id)
        raise HTTPException(
            status_code=500,
            detail="Document processing failed. Please try again.",
        ) from exc

    logger.info(
        "Document uploaded: document_id=%s user_id=%s chunks=%s",
        document_id,
        user_id,
        chunk_count,
    )
    return {
        "message": "Document uploaded successfully.",
        **{
            key: saved_record[key]
            for key in (
                "document_id",
                "filename",
                "file_hash",
                "file_size",
                "chunk_count",
                "file_type",
            )
        },
    }


@router.get("/", response_model=DocumentListResponse)
def list_documents(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user_id = str(current_user["user_id"])
    try:
        documents = list_user_documents(user_id, current_user["access_token"])
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        logger.error("Supabase document listing failed.")
        raise _service_unavailable() from exc
    return {
        "documents": [
            {
                key: document[key]
                for key in (
                    "document_id",
                    "filename",
                    "file_hash",
                    "file_size",
                    "chunk_count",
                    "file_type",
                )
            }
            for document in documents
        ]
    }


@router.delete("/{document_id}", status_code=204, response_class=Response)
def remove_document(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user_id = str(current_user["user_id"])
    access_token = str(current_user["access_token"])

    try:
        document = get_user_document(document_id, user_id, access_token)
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        logger.error("Supabase document lookup failed during deletion.")
        raise _service_unavailable() from exc
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    object_path = f"{user_id}/{document_id}{document['file_type']}"
    try:
        delete_document(document_id, user_id=user_id)
        delete_document_object(object_path, access_token)
        delete_document_record(document_id, user_id, access_token)
    except ServiceUnavailableError as exc:
        logger.error("Qdrant deletion failed: document_id=%s", document_id)
        raise _service_unavailable() from exc
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        logger.error("Supabase deletion failed: document_id=%s", document_id)
        raise _service_unavailable() from exc

    logger.info("Document deleted: document_id=%s user_id=%s", document_id, user_id)
    return Response(status_code=204)
