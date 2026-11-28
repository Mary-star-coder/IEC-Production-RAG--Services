
from uuid import uuid4

import pytest

from app.ingestion.vector_store import (
    add_chunks,
    delete_document,
    document_exists,
    get_collection_count,
    search_chunks,
)
from app.ingestion import vector_store


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


def test_qdrant_chunk_round_trip():
    """Verify Qdrant stores, filters, retrieves, and deletes document chunks."""

    document_id = str(uuid4())
    user_id = f"test-{uuid4()}"
    chunk = {
        "text": "Qdrant stores this searchable test passage.",
        "page": 1,
        "position": 0,
    }

    try:
        assert add_chunks(
            document_id,
            "qdrant-test.txt",
            [chunk],
            user_id=user_id,
            file_hash="a" * 64,
        ) == 1
        assert get_collection_count(user_id=user_id) == 1
        assert document_exists("a" * 64, user_id=user_id)
        assert not document_exists("b" * 64, user_id=user_id)

        results = search_chunks(
            "searchable test passage",
            top_k=1,
            user_id=user_id,
        )

        assert len(results) == 1
        assert results[0]["text"] == chunk["text"]
        assert results[0]["metadata"]["user_id"] == user_id

    finally:
        delete_document(document_id, user_id=user_id)

    assert get_collection_count(user_id=user_id) == 0


def test_search_respects_selected_documents():
    user_id = f"test-{uuid4()}"
    first_document_id = str(uuid4())
    second_document_id = str(uuid4())
    chunk = {
        "text": "Selected document search test passage.",
        "page": 1,
        "position": 0,
    }

    try:
        add_chunks(
            first_document_id,
            "first.txt",
            [chunk],
            user_id=user_id,
        )
        add_chunks(
            second_document_id,
            "second.txt",
            [chunk],
            user_id=user_id,
        )
        results = search_chunks(
            "selected document search",
            user_id=user_id,
            document_ids=[second_document_id],
        )

        assert results
        assert {
            result["metadata"]["document_id"] for result in results
        } == {second_document_id}
    finally:
        delete_document(first_document_id, user_id=user_id)
        delete_document(second_document_id, user_id=user_id)


def test_empty_document_filter_skips_retrieval(monkeypatch):
    monkeypatch.setattr(
        vector_store,
        "embed_texts",
        lambda *args, **kwargs: pytest.fail("No documents are selected"),
    )

    assert search_chunks(
        "valid question",
        user_id="test-user",
        document_ids=[],
    ) == []
