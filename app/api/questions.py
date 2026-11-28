
# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

import hashlib
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import ValidationError

from app.exceptions import ServiceUnavailableError
from app.schemas import QuestionRequest, QuestionResponse
from app.ingestion.vector_store import search_chunks
from app.integrations.supabase import (
    SupabaseAPIError,
    SupabaseUnavailableError,
    get_cached_answer,
    get_chat_session,
    list_chat_turns,
    save_chat_turn,
    save_cached_answer,
)

from app.generation import (
    generate_citations,
)
from app.gemini import generate_grounded_answer

from app.evaluation.answer_evaluation import evaluate_answer

# Import question validation and its maximum permitted length.
from app.guardrails import validate_question, MAX_QUESTION_LENGTH

# Import the configured minimum similarity threshold.
from app.config import SIMILARITY_THRESHOLD

# Import authentication dependency to identify the current user.
from app.auth.dependencies import get_current_user


# ---------------------------------------------------------
# ROUTER AND LOGGING CONFIGURATION
# ---------------------------------------------------------

logger = logging.getLogger("production_rag.questions")

def _question_hash(
    question: str,
    document_ids: list[str] | None,
    history: list[dict[str, Any]],
) -> str:
    normalized_question = " ".join(question.split()).casefold()
    cache_key = json.dumps(
        {
            "question": normalized_question,
            "document_ids": (
                None if document_ids is None else sorted(set(document_ids))
            ),
            "history": [
                {
                    "question": turn.get("question", ""),
                    "answer": turn.get("answer", ""),
                }
                for turn in history[-6:]
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(cache_key.encode("utf-8")).hexdigest()


def _retrieval_query(
    question: str,
    history: list[dict[str, Any]],
) -> str:
    if not history:
        return question

    context = []
    for turn in history[-4:]:
        previous_question = str(turn.get("question", "")).strip()
        previous_answer = str(turn.get("answer", "")).strip()
        if previous_question:
            context.append(f"Previous question: {previous_question[:500]}")
        if previous_answer:
            context.append(f"Previous answer: {previous_answer[:1000]}")

    return "\n".join([*context, f"Current question: {question}"])


def _chat_title(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= 80 else f"{title[:77].rstrip()}..."


def _save_question_response(
    *,
    user_id: str,
    question_hash: str,
    top_k: int,
    response: dict[str, Any],
    access_token: str,
) -> None:
    try:
        save_cached_answer(
            user_id,
            question_hash,
            top_k,
            response,
            access_token,
        )
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        logger.error("Question response cache write failed: user_id=%s", user_id)
        raise ServiceUnavailableError(
            "Question cache is temporarily unavailable."
        ) from exc


def _save_chat_response(
    *,
    chat: dict[str, Any] | None,
    chat_id: str | None,
    user_id: str,
    question: str,
    document_ids: list[str] | None,
    response: dict[str, Any],
    access_token: str,
) -> None:
    if chat is None or chat_id is None:
        return
    title = str(chat.get("title") or "").strip()
    if not title or title == "New chat":
        title = _chat_title(question)
    try:
        save_chat_turn(
            chat_id=chat_id,
            user_id=user_id,
            title=title,
            question=question,
            answer=response["answer"],
            citations=response["citations"],
            retrieved_chunks=response["retrieved_chunks"],
            selected_document_ids=document_ids,
            abstained=response["abstained"],
            access_token=access_token,
        )
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        logger.error("Chat turn could not be saved: user_id=%s", user_id)
        raise HTTPException(
            status_code=503,
            detail="Chat history is temporarily unavailable. Please try again.",
        ) from exc


router = APIRouter(
    prefix="/api/questions",
    tags=["Questions"],
)


# ---------------------------------------------------------
# QUESTION-ANSWERING ENDPOINT
# ---------------------------------------------------------

@router.post(
    "/ask",
    response_model=QuestionResponse,
    summary="Ask a question about uploaded documents",
    description=(
        "Retrieves relevant chunks from the authenticated user's documents "
        "and returns a source-grounded answer with citations. "
        "Questions must contain between 3 and 1000 characters. "
        "Returns an abstention response when relevant information is unavailable."
    ),
)
def ask_question(
    request: QuestionRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Answer questions using only the authenticated user's documents.

    The endpoint validates input, retrieves relevant document chunks,
    generates a Gemini answer from retrieved sources, and returns citations.
    """

    # Normalize the question and identify the authenticated user.
    question = request.question.strip()
    user_id = str(current_user["user_id"])

    # -----------------------------------------------------
    # INPUT VALIDATION
    # -----------------------------------------------------

    # Reject empty or whitespace-only questions.
    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    # Reject questions exceeding the configured character limit.
    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=422,
            detail="Question exceeds the maximum allowed length of 1000 characters.",
        )

    # Detect and reject known prompt-injection attempts.
    if not validate_question(question):
        logger.warning(
            "Potential prompt injection detected: user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=400,
            detail="Potential prompt injection detected.",
        )

    access_token = str(current_user["access_token"])
    chat_id = str(request.chat_id) if request.chat_id is not None else None
    document_ids = (
        None
        if request.document_ids is None
        else list(dict.fromkeys(str(document_id) for document_id in request.document_ids))
    )
    chat = None
    history: list[dict[str, Any]] = []
    if chat_id is not None:
        try:
            chat = get_chat_session(chat_id, user_id, access_token)
            if chat is None:
                raise HTTPException(status_code=404, detail="Chat not found.")
            history = list_chat_turns(chat_id, user_id, access_token)
        except (SupabaseAPIError, SupabaseUnavailableError) as exc:
            logger.error("Chat history could not be loaded: user_id=%s", user_id)
            raise HTTPException(
                status_code=503,
                detail="Chat history is temporarily unavailable. Please try again.",
            ) from exc

    question_hash = _question_hash(question, document_ids, history)
    try:
        cached_response = get_cached_answer(
            user_id,
            question_hash,
            request.top_k,
            access_token,
        )
    except (SupabaseAPIError, SupabaseUnavailableError) as exc:
        logger.error("Question response cache lookup failed: user_id=%s", user_id)
        raise HTTPException(
            status_code=503,
            detail="Question service is temporarily unavailable. Please try again.",
        ) from exc

    if cached_response is not None:
        try:
            cached_response = QuestionResponse.model_validate(
                cached_response
            ).model_dump()
        except ValidationError as exc:
            logger.exception(
                "Cached question response is invalid: user_id=%s",
                user_id,
            )
            raise HTTPException(
                status_code=503,
                detail="Question service is temporarily unavailable. Please try again.",
            ) from exc
        _save_chat_response(
            chat=chat,
            chat_id=chat_id,
            user_id=user_id,
            question=question,
            document_ids=document_ids,
            response=cached_response,
            access_token=access_token,
        )
        return cached_response

    try:
        # -------------------------------------------------
        # DOCUMENT RETRIEVAL
        # -------------------------------------------------

        # Retrieve only chunks belonging to the authenticated user.
        retrieval_query = _retrieval_query(question, history)
        if document_ids is None:
            matches = search_chunks(
                retrieval_query,
                top_k=request.top_k,
                user_id=user_id,
            )
        else:
            matches = search_chunks(
                retrieval_query,
                top_k=request.top_k,
                user_id=user_id,
                document_ids=document_ids,
            )

        # Default response when no sufficiently relevant
        # information is available in the uploaded documents.
        abstention_answer = (
            "I could not find relevant information in the uploaded documents."
        )

        # Keep only chunks that satisfy the configured similarity threshold.
        relevant_matches = [
            match
            for match in matches
            if match["similarity"] >= SIMILARITY_THRESHOLD
        ]

        # -------------------------------------------------
        # ABSTENTION HANDLING
        # -------------------------------------------------

        # Refuse to generate an answer when no relevant chunks are found.
        if not relevant_matches:
            evaluation = evaluate_answer(
                answer=abstention_answer,
                retrieved_chunks=matches,
                citations=[],
                abstained=True,
            )

            logger.info(
                "Question answered with abstention: "
                "user_id=%s retrieved_count=%s",
                user_id,
                len(matches),
            )

            response = {
                "answer": abstention_answer,
                "citations": [],
                "retrieved_chunks": matches,
                "retrieved_count": len(matches),
                "abstained": True,
                "answer_evaluation": evaluation,
            }
            _save_chat_response(
                chat=chat,
                chat_id=chat_id,
                user_id=user_id,
                question=question,
                document_ids=document_ids,
                response=response,
                access_token=access_token,
            )
            _save_question_response(
                user_id=user_id,
                question_hash=question_hash,
                top_k=request.top_k,
                response=response,
                access_token=access_token,
            )
            return response

        # -------------------------------------------------
        # GROUNDED ANSWER GENERATION
        # -------------------------------------------------

        if history:
            answer = generate_grounded_answer(
                question,
                relevant_matches,
                conversation_history=history,
            )
        else:
            answer = generate_grounded_answer(question, relevant_matches)

        # Generate citations using retrieved source metadata.
        citations = generate_citations(relevant_matches)

        # -------------------------------------------------
        # ANSWER EVALUATION
        # -------------------------------------------------

        # Perform structural checks on the answer and its citations.
        evaluation = evaluate_answer(
            answer=answer,
            retrieved_chunks=relevant_matches,
            citations=citations,
            abstained=False,
        )

        # Log successful question processing without exposing document content.
        logger.info(
            "Question answered successfully: "
            "user_id=%s retrieved_count=%s citations=%s",
            user_id,
            len(relevant_matches),
            len(citations),
        )

        # Return the answer, citations, and actual retrieved chunks.
        response = {
            "answer": answer,
            "citations": citations,
            "retrieved_chunks": relevant_matches,
            "retrieved_count": len(relevant_matches),
            "abstained": False,
            "answer_evaluation": evaluation,
        }
        _save_chat_response(
            chat=chat,
            chat_id=chat_id,
            user_id=user_id,
            question=question,
            document_ids=document_ids,
            response=response,
            access_token=access_token,
        )
        _save_question_response(
            user_id=user_id,
            question_hash=question_hash,
            top_k=request.top_k,
            response=response,
            access_token=access_token,
        )
        return response

    except HTTPException:
        # Preserve intentional HTTP errors without changing their status codes.
        raise

    except ServiceUnavailableError:
        # Return a controlled response if a question dependency is unavailable.
        logger.exception(
            "Question dependency unavailable: user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Question service is temporarily unavailable. "
                "Please try again."
            ),
        )

    except Exception:
        # Avoid exposing internal exception details to API clients.
        logger.exception(
            "Question processing failed: user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Question processing failed. Please try again.",
        )
