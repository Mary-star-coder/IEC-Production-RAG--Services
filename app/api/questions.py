
import logging

from fastapi import APIRouter, HTTPException

from app.schemas import QuestionRequest, QuestionResponse
from app.ingestion.vector_store import search_chunks

from app.generation import (
    generate_extractive_answer,
    generate_citations,
)

from app.evaluation.answer_evaluation import evaluate_answer
from app.guardrails import validate_question
from app.config import SIMILARITY_THRESHOLD


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
def ask_question(request: QuestionRequest):
    """
    Answer a question using retrieved document evidence.

    The workflow validates input, retrieves relevant chunks,
    applies similarity filtering, generates an extractive answer,
    creates citations, and evaluates the response.
    """

    question = request.question.strip()

    # Reject empty questions.
    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    # Apply basic prompt-injection detection.
    if not validate_question(question):
        logger.warning("Potential prompt injection detected.")
        raise HTTPException(
            status_code=400,
            detail="Potential prompt injection detected.",
        )

    try:
        # Retrieve relevant document chunks.
        matches = search_chunks(
            question,
            top_k=request.top_k,
        )

        abstention_answer = (
            "I could not find relevant information in the uploaded documents."
        )

        # Apply the configured similarity threshold.
        relevant_matches = [
            match for match in matches
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
                "Question answered with abstention: retrieved_count=%s",
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
            "Question answered successfully: retrieved_count=%s citations=%s",
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

    except Exception:
        # Keep internal exception details in server logs only.
        logger.exception("Question processing failed.")

        raise HTTPException(
            status_code=500,
            detail="Question processing failed. Please try again.",
        )
