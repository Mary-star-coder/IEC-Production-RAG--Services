
from app.evaluation.answer_evaluation import evaluate_answer


def test_answer_with_valid_sources():
    """Verify that an answer matching retrieved content passes evaluation."""

    # Prepare a retrieved source chunk containing the answer information.
    chunks = [{"text": "Machine learning uses training data."}]

    # Provide a citation that identifies the source document and page.
    citations = [{"filename": "notes.pdf", "page": 1}]

    answer = "Machine learning uses training data."

    result = evaluate_answer(
        answer=answer,
        retrieved_chunks=chunks,
        citations=citations,
        abstained=False,
    )

    # The answer should pass because it matches the source and includes a citation.
    assert result["passed"] is True
    assert result["checks"]["citations_present"] is True
    assert result["checks"]["answer_matches_retrieved_source"] is True


def test_answer_without_citations():
    """Verify that an answer without citations fails the evaluation."""

    chunks = [{"text": "Machine learning uses training data."}]

    result = evaluate_answer(
        answer="Machine learning uses training data.",
        retrieved_chunks=chunks,
        citations=[],
        abstained=False,
    )

    # A source-supported answer must include citations.
    assert result["passed"] is False
    assert result["checks"]["citations_present"] is False


def test_abstention_response():
    """Verify that a valid abstention response passes evaluation."""

    # This is the expected response when the uploaded documents lack relevant information.
    answer = "I could not find relevant information in the uploaded documents."

    result = evaluate_answer(
        answer=answer,
        retrieved_chunks=[],
        citations=[],
        abstained=True,
    )

    # A valid abstention should contain an abstention message and no citations.
    assert result["passed"] is True
    assert result["checks"]["abstention_message_present"] is True
    assert result["checks"]["citations_empty"] is True


def test_empty_answer_fails():
    """Verify that an empty answer does not pass evaluation."""

    result = evaluate_answer(
        answer="",
        retrieved_chunks=[{"text": "Some source text."}],
        citations=[{"filename": "notes.pdf"}],
        abstained=False,
    )

    # An empty answer is invalid even if retrieved content and citations exist.
    assert result["passed"] is False
    assert result["checks"]["answer_not_empty"] is False
