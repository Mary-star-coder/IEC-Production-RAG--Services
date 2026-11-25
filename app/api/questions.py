
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Depends

from app.exceptions import ServiceUnavailableError
from app.schemas import QuestionRequest, QuestionResponse
from app.ingestion.vector_store import search_chunks

from app.generation import (
    generate_extractive_answer,
    generate_citations,
)

from app.evaluation.answer_evaluation import evaluate_answer
from app.guardrails import validate_question
from app.config import SIMILARITY_THRESHOLD
from app.auth.dependencies import get_current_user


# ---------------------------------------------------------
# ROUTER AND LOGGING CONFIGURATION
# ---------------------------------------------------------

logger = logging.getLogger("production_rag.questions")

router = APIRouter(
    prefix="/api/questions",
    tags=["Questions"],
)


# ---------------------------------------------------------
# QUESTION-ANSWERING ENDPOINT
# ---------------------------------------------------------

@router.post("/ask", response_model=QuestionResponse)
def ask_question(
    request: QuestionRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Answer questions using only the authenticated user's documents.
    """

    question = request.question.strip()
    user_id = str(current_user["user_id"])

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    if not validate_question(question):
        logger.warning(
            "Potential prompt injection detected: user_id=%s",
            user_id,
        )
        raise HTTPException(
            status_code=400,
            detail="Potential prompt injection detected.",
        )

    try:
        # Retrieve chunks belonging only to the authenticated user.
        matches = search_chunks(
            question,
            top_k=request.top_k,
            user_id=user_id,
        )

        abstention_answer = (
            "I could not find relevant information in the uploaded documents."
        )

        relevant_matches = [
            match
            for match in matches
            if match["similarity"] >= SIMILARITY_THRESHOLD
        ]

        # -----------------------------------------------------
        # ABSTENTION HANDLING
        # -----------------------------------------------------

        if not relevant_matches:
            evaluation = evaluate_answer(
                answer=abstention_answer,
                retrieved_chunks=matches,
                citations=[],
                abstained=True,
            )

            logger.info(
                "Question answered with abstention: user_id=%s retrieved_count=%s",
                user_id,
                len(matches),
            )

            return {
                "answer": abstention_answer,
                "citations": [],
                "retrieved_chunks": matches,
                "retrieved_count": len(matches),
                "abstained": True,
                "answer_evaluation": evaluation,
            }

        # -----------------------------------------------------
        # EXTRACTIVE ANSWER GENERATION
        # -----------------------------------------------------

        answer = generate_extractive_answer(relevant_matches)

        citations = generate_citations(relevant_matches)

        # -----------------------------------------------------
        # ANSWER EVALUATION
        # -----------------------------------------------------

        evaluation = evaluate_answer(
            answer=answer,
            retrieved_chunks=relevant_matches,
            citations=citations,
            abstained=False,
        )

        logger.info(
            "Question answered successfully: user_id=%s retrieved_count=%s citations=%s",
            user_id,
            len(relevant_matches),
            len(citations),
        )

        return {
            "answer": answer,
            "citations": citations,
            "retrieved_chunks": relevant_matches,
            "retrieved_count": len(relevant_matches),
            "abstained": False,
            "answer_evaluation": evaluation,
        }

    except HTTPException:
        raise

    except ServiceUnavailableError:
        logger.exception(
            "Vector database unavailable: user_id=%s",
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
        logger.exception(
            "Question processing failed: user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Question processing failed. Please try again.",
        )
