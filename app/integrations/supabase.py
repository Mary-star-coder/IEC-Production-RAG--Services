from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from app.config import (
    SUPABASE_PASSWORD_RESET_REDIRECT_URL,
    SUPABASE_PUBLISHABLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_URL,
)


_TIMEOUT_SECONDS = 15.0
_DOCUMENT_COLUMNS = (
    "document_id,filename,file_hash,file_size,chunk_count,file_type,"
    "owner_user_id,created_at"
)


class SupabaseAPIError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        retry_after: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.retry_after = retry_after


class SupabaseUnavailableError(Exception):
    """Raised when Supabase is unconfigured or cannot be reached."""


def _request(
    method: str,
    path: str,
    *,
    access_token: str | None = None,
    params: dict[str, str] | None = None,
    json_body: Any = None,
    content: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise SupabaseUnavailableError("Supabase configuration is missing.")

    headers = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token or SUPABASE_PUBLISHABLE_KEY}",
    }
    if extra_headers:
        headers.update(extra_headers)

    try:
        response = httpx.request(
            method,
            f"{SUPABASE_URL}{path}",
            headers=headers,
            params=params,
            json=json_body,
            content=content,
            timeout=_TIMEOUT_SECONDS,
        )
    except httpx.RequestError as exc:
        raise SupabaseUnavailableError(
            "Supabase could not be reached."
        ) from exc

    if response.is_error:
        try:
            error_body = response.json()
        except ValueError:
            error_body = {}
        message = "Supabase rejected the request."
        if isinstance(error_body, dict):
            message = (
                error_body.get("msg")
                or error_body.get("message")
                or message
            )
        raise SupabaseAPIError(
            response.status_code,
            str(message),
            retry_after=response.headers.get("Retry-After"),
        )
    return response


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise SupabaseUnavailableError(
            "Supabase returned an invalid response."
        ) from exc


def _session_result(
    data: dict[str, Any],
    *,
    email_fallback: str | None = None,
) -> dict[str, Any]:
    user = data.get("user") or {}
    user_id = user.get("id")
    email = user.get("email") or email_fallback
    if not user_id or not email:
        raise SupabaseUnavailableError("Supabase returned an incomplete user.")
    access_token = data.get("access_token")
    return {
        "user_id": str(user_id),
        "email": str(email),
        "access_token": access_token,
        "refresh_token": data.get("refresh_token"),
        "requires_email_confirmation": not bool(access_token),
    }


def register_user(email: str, password: str) -> dict[str, Any]:
    data = _json(_request(
        "POST",
        "/auth/v1/signup",
        json_body={"email": email, "password": password},
    ))
    if not isinstance(data, dict):
        raise SupabaseUnavailableError(
            "Supabase returned an invalid registration response."
        )
    return _session_result(data, email_fallback=email)


def login_user(email: str, password: str) -> dict[str, Any]:
    data = _json(_request(
        "POST",
        "/auth/v1/token",
        params={"grant_type": "password"},
        json_body={"email": email, "password": password},
    ))
    if not isinstance(data, dict):
        raise SupabaseUnavailableError(
            "Supabase returned an invalid login response."
        )
    return _session_result(data, email_fallback=email)


def refresh_user_session(refresh_token: str) -> dict[str, Any]:
    data = _json(_request(
        "POST",
        "/auth/v1/token",
        params={"grant_type": "refresh_token"},
        json_body={"refresh_token": refresh_token},
    ))
    if not isinstance(data, dict):
        raise SupabaseUnavailableError(
            "Supabase returned an invalid session response."
        )
    return _session_result(data)


def send_password_reset_email(email: str) -> None:
    params = {}
    if SUPABASE_PASSWORD_RESET_REDIRECT_URL:
        params["redirect_to"] = SUPABASE_PASSWORD_RESET_REDIRECT_URL
    _request(
        "POST",
        "/auth/v1/recover",
        params=params,
        json_body={"email": email},
    )


def update_user_password(access_token: str, password: str) -> None:
    _request(
        "PUT",
        "/auth/v1/user",
        access_token=access_token,
        json_body={"password": password},
    )


def get_authenticated_user(access_token: str) -> dict[str, Any]:
    data = _json(_request(
        "GET",
        "/auth/v1/user",
        access_token=access_token,
    ))
    if not isinstance(data, dict) or not data.get("id"):
        raise SupabaseAPIError(401, "Invalid authentication token.")
    return data


def find_duplicate_document(
    user_id: str,
    file_hash: str,
    access_token: str,
) -> bool:
    response = _request(
        "GET",
        "/rest/v1/documents",
        access_token=access_token,
        params={
            "select": "document_id",
            "owner_user_id": f"eq.{user_id}",
            "file_hash": f"eq.{file_hash}",
            "limit": "1",
        },
    )
    rows = _json(response)
    return isinstance(rows, list) and bool(rows)


def get_cached_answer(
    user_id: str,
    question_hash: str,
    top_k: int,
    access_token: str,
) -> dict[str, Any] | None:
    response = _request(
        "GET",
        "/rest/v1/question_cache",
        access_token=access_token,
        params={
            "select": "response",
            "user_id": f"eq.{user_id}",
            "question_hash": f"eq.{question_hash}",
            "top_k": f"eq.{top_k}",
            "limit": "1",
        },
    )
    rows = _json(response)
    if not isinstance(rows, list):
        raise SupabaseUnavailableError(
            "Supabase returned an invalid question cache response."
        )
    if not rows:
        return None
    if not isinstance(rows[0], dict):
        raise SupabaseUnavailableError(
            "Supabase returned an invalid cached answer."
        )

    cached_response = rows[0].get("response")
    if not isinstance(cached_response, dict):
        raise SupabaseUnavailableError(
            "Supabase returned an invalid cached answer."
        )
    return cached_response


def save_cached_answer(
    user_id: str,
    question_hash: str,
    top_k: int,
    response: dict[str, Any],
    access_token: str,
) -> None:
    _request(
        "POST",
        "/rest/v1/question_cache",
        access_token=access_token,
        params={"on_conflict": "user_id,question_hash,top_k"},
        json_body={
            "user_id": user_id,
            "question_hash": question_hash,
            "top_k": top_k,
            "response": response,
        },
        extra_headers={
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )


def list_user_documents(
    user_id: str,
    access_token: str,
) -> list[dict[str, Any]]:
    response = _request(
        "GET",
        "/rest/v1/documents",
        access_token=access_token,
        params={
            "select": _DOCUMENT_COLUMNS,
            "owner_user_id": f"eq.{user_id}",
            "order": "created_at.desc",
        },
    )
    rows = _json(response)
    if not isinstance(rows, list):
        raise SupabaseUnavailableError("Supabase returned invalid documents.")
    return rows


def get_user_document(
    document_id: str,
    user_id: str,
    access_token: str,
) -> dict[str, Any] | None:
    response = _request(
        "GET",
        "/rest/v1/documents",
        access_token=access_token,
        params={
            "select": _DOCUMENT_COLUMNS,
            "document_id": f"eq.{document_id}",
            "owner_user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )
    rows = _json(response)
    return rows[0] if isinstance(rows, list) and rows else None


def create_document_record(
    record: dict[str, Any],
    access_token: str,
) -> dict[str, Any]:
    response = _request(
        "POST",
        "/rest/v1/documents",
        access_token=access_token,
        json_body=record,
        extra_headers={"Prefer": "return=representation"},
    )
    rows = _json(response)
    if not isinstance(rows, list) or not rows:
        raise SupabaseUnavailableError(
            "Supabase did not confirm the document record."
        )
    return rows[0]


def delete_document_record(
    document_id: str,
    user_id: str,
    access_token: str,
) -> None:
    _request(
        "DELETE",
        "/rest/v1/documents",
        access_token=access_token,
        params={
            "document_id": f"eq.{document_id}",
            "owner_user_id": f"eq.{user_id}",
        },
    )


def upload_document_object(
    object_path: str,
    content: bytes,
    content_type: str,
    access_token: str,
) -> None:
    bucket = quote(SUPABASE_STORAGE_BUCKET, safe="")
    path = quote(object_path, safe="/")
    _request(
        "POST",
        f"/storage/v1/object/{bucket}/{path}",
        access_token=access_token,
        content=content,
        extra_headers={
            "Content-Type": content_type,
            "x-upsert": "false",
        },
    )


def delete_document_object(object_path: str, access_token: str) -> None:
    bucket = quote(SUPABASE_STORAGE_BUCKET, safe="")
    _request(
        "DELETE",
        f"/storage/v1/object/{bucket}",
        access_token=access_token,
        json_body={"prefixes": [object_path]},
    )


def list_user_chats(
    user_id: str,
    access_token: str,
) -> list[dict[str, Any]]:
    response = _request(
        "GET",
        "/rest/v1/chat_sessions",
        access_token=access_token,
        params={
            "select": "id,title,created_at,updated_at",
            "user_id": f"eq.{user_id}",
            "order": "updated_at.desc",
            "limit": "100",
        },
    )
    rows = _json(response)
    if not isinstance(rows, list):
        raise SupabaseUnavailableError("Supabase returned invalid chats.")
    return rows


def create_chat_session(
    user_id: str,
    title: str,
    access_token: str,
) -> dict[str, Any]:
    response = _request(
        "POST",
        "/rest/v1/chat_sessions",
        access_token=access_token,
        json_body={"user_id": user_id, "title": title},
        extra_headers={"Prefer": "return=representation"},
    )
    rows = _json(response)
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise SupabaseUnavailableError(
            "Supabase did not confirm the chat session."
        )
    return rows[0]


def get_chat_session(
    chat_id: str,
    user_id: str,
    access_token: str,
) -> dict[str, Any] | None:
    response = _request(
        "GET",
        "/rest/v1/chat_sessions",
        access_token=access_token,
        params={
            "select": "id,title,created_at,updated_at",
            "id": f"eq.{chat_id}",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )
    rows = _json(response)
    return rows[0] if isinstance(rows, list) and rows else None


def list_chat_turns(
    chat_id: str,
    user_id: str,
    access_token: str,
) -> list[dict[str, Any]]:
    response = _request(
        "GET",
        "/rest/v1/chat_turns",
        access_token=access_token,
        params={
            "select": (
                "id,chat_id,question,answer,citations,retrieved_chunks,"
                "selected_document_ids,abstained,created_at"
            ),
            "chat_id": f"eq.{chat_id}",
            "user_id": f"eq.{user_id}",
            "order": "created_at.asc",
        },
    )
    rows = _json(response)
    if not isinstance(rows, list):
        raise SupabaseUnavailableError(
            "Supabase returned invalid chat history."
        )
    return rows


def save_chat_turn(
    *,
    chat_id: str,
    user_id: str,
    title: str,
    question: str,
    answer: str,
    citations: list[dict[str, Any]],
    retrieved_chunks: list[dict[str, Any]],
    selected_document_ids: list[str] | None,
    abstained: bool,
    access_token: str,
) -> None:
    _request(
        "POST",
        "/rest/v1/chat_turns",
        access_token=access_token,
        json_body={
            "chat_id": chat_id,
            "user_id": user_id,
            "question": question,
            "answer": answer,
            "citations": citations,
            "retrieved_chunks": retrieved_chunks,
            "selected_document_ids": selected_document_ids,
            "abstained": abstained,
        },
        extra_headers={"Prefer": "return=minimal"},
    )
    _request(
        "PATCH",
        "/rest/v1/chat_sessions",
        access_token=access_token,
        params={
            "id": f"eq.{chat_id}",
            "user_id": f"eq.{user_id}",
        },
        json_body={
            "title": title,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        extra_headers={"Prefer": "return=minimal"},
    )


def delete_chat_session(
    chat_id: str,
    user_id: str,
    access_token: str,
) -> None:
    _request(
        "DELETE",
        "/rest/v1/chat_sessions",
        access_token=access_token,
        params={
            "id": f"eq.{chat_id}",
            "user_id": f"eq.{user_id}",
        },
    )
