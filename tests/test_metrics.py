
from app.evaluation.metrics import (
    hit_rate_at_k,
    recall_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
)


def test_hit_rate_at_k():
    """Check whether at least one relevant result appears in the top-k results."""

    # A relevant item ("b") is present in the first two results.
    assert hit_rate_at_k(["a", "b", "c"], ["b"], k=2) == 1.0

    # No relevant item is present in the first two results.
    assert hit_rate_at_k(["a", "b", "c"], ["d"], k=2) == 0.0


def test_recall_at_k():
    """Check the proportion of relevant items retrieved within the top-k results."""

    # Two items are relevant ("a" and "c"), but only "a" appears in the top two.
    # Therefore, recall is 1 out of 2 relevant items.
    assert recall_at_k(["a", "b", "c"], ["a", "c"], k=2) == 0.5


def test_reciprocal_rank():
    """Check the reciprocal rank of the first relevant result."""

    # The first relevant result is at position 2, so reciprocal rank is 1/2.
    assert reciprocal_rank(["a", "b", "c"], ["b"]) == 0.5

    # No relevant result is found, so reciprocal rank is zero.
    assert reciprocal_rank(["a", "b"], ["c"]) == 0.0


def test_mean_reciprocal_rank():
    """Check that MRR is calculated as the average reciprocal rank."""

    results = [
        (["a", "b"], ["a"]),  # First result is relevant: reciprocal rank = 1.0.
        (["a", "b"], ["b"]),  # Second result is relevant: reciprocal rank = 0.5.
    ]

    # Mean reciprocal rank = (1.0 + 0.5) / 2 = 0.75.
    assert mean_reciprocal_rank(results) == 0.75


def test_empty_relevant_ids():
    """Verify that metrics return zero when no relevant IDs are provided."""

    # Without relevant document IDs, no result can count as a successful retrieval.
    assert hit_rate_at_k(["a"], []) == 0.0
    assert recall_at_k(["a"], []) == 0.0
    assert reciprocal_rank(["a"], []) == 0.0


def test_empty_results():
    """Verify that MRR returns zero when the evaluation dataset is empty."""

    # There are no query-result pairs to evaluate.
    assert mean_reciprocal_rank([]) == 0.0
