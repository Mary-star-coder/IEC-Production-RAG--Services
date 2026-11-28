import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth.dependencies import get_current_user
from app.integrations.supabase import (
    SupabaseAPIError,
    SupabaseUnavailableError,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    list_chat_turns,
    list_user_chats,
)
from app.schemas import ChatSessionCreateRequest


logger = logging.getLogger("production_rag.chats")
router = APIRouter(prefix="/api/chats", tags=["Chats"])


def _unavailable(exc: Exception) -> HTTPException:
    if isinstance(exc, SupabaseAPIError):
        logger.error("Chat storage failed: status=%s", exc.status_code)
        if exc.status_code == 404:
            return HTTPException(
                status_code=503,
                detail=(
                    "Chat history tables are missing in Supabase. "
                    "Run the updated supabase/schema.sql in the SQL Editor."
                ),
            )
    else:
        logger.error("Chat storage could not reach Supabase.")
    return HTTPException(
        status_code=503,
        detail="Chat history is temporarily unavailable. Please try again.",
    )


@router.get("/")
def list_chats(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user_id = str(current_user["user_id"])
    try:
        return {
            "chats": list_user_chats(
                user_id,
                str(current_user["access_token"]),
            )
        }
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        raise _unavailable(exc) from exc


@router.post("/", status_code=201)
def create_chat(
    request: ChatSessionCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    title = request.title.strip()
    if not title:
        raise HTTPException(
            status_code=422,
            detail="Chat title cannot be empty.",
        )
    try:
        chat = create_chat_session(
            str(current_user["user_id"]),
            title,
            str(current_user["access_token"]),
        )
        return {"chat": chat}
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        raise _unavailable(exc) from exc


@router.get("/{chat_id}")
def get_chat(
    chat_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user_id = str(current_user["user_id"])
    access_token = str(current_user["access_token"])
    chat_id_str = str(chat_id)
    try:
        chat = get_chat_session(chat_id_str, user_id, access_token)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found.")
        return {
            "chat": chat,
            "turns": list_chat_turns(chat_id_str, user_id, access_token),
        }
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        raise _unavailable(exc) from exc


@router.delete("/{chat_id}", status_code=204)
def remove_chat(
    chat_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    user_id = str(current_user["user_id"])
    access_token = str(current_user["access_token"])
    chat_id_str = str(chat_id)
    try:
        chat = get_chat_session(chat_id_str, user_id, access_token)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found.")
        delete_chat_session(chat_id_str, user_id, access_token)
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        raise _unavailable(exc) from exc
    return Response(status_code=204)
