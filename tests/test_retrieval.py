
from app.ingestion.vector_store import search_chunks


def test_search_empty_query():
    """Verify that an empty search query raises a ValueError."""

    try:
        search_chunks("")
        # Fail the test if the function does not reject an empty query.
        assert False, "Expected ValueError for empty query"
    except ValueError as exc:
        # Confirm that the function returns the expected validation message.
        assert str(exc) == "Query cannot be empty."


def test_search_invalid_top_k():
    """Verify that top_k must be a positive integer."""

    try:
        # A top_k value of zero is invalid because no results were requested.
        search_chunks("machine learning", top_k=0)
        assert False, "Expected ValueError for invalid top_k"
    except ValueError as exc:
        # Check the error message for invalid top_k input.
        assert str(exc) == "top_k must be greater than zero."


def test_search_returns_list():
    """Verify that the vector search function returns a list of results."""

    results = search_chunks("machine learning", top_k=3)

    # The search response should always be a list, even if no matches are found.
    assert isinstance(results, list)


def test_search_result_structure():
    """Verify that each retrieved result contains the required fields."""

    results = search_chunks("machine learning", top_k=3)

    # Check the structure when the vector database returns at least one result.
    if results:
        result = results[0]

        # Each result should include its text, metadata, distance, and similarity.
        assert "text" in result
        assert "metadata" in result
        assert "distance" in result
        assert "similarity" in result
