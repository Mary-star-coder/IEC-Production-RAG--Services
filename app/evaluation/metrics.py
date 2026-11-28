
# ---------------------------------------------------------
# METRIC INPUT VALIDATION
# ---------------------------------------------------------

def _validate_k(k: int) -> None:
    """Ensure k is a positive integer."""

    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k must be a positive integer.")


def _as_set(values) -> set:
    """Normalize IDs into a set to avoid duplicate counting."""

    if values is None:
        return set()

    return set(values)


# ---------------------------------------------------------
# HIT RATE AT K
# ---------------------------------------------------------

def hit_rate_at_k(retrieved_ids, relevant_ids, k: int = 5) -> float:
    """
    Return 1.0 if at least one relevant item appears in top-k.

    Otherwise return 0.0.
    """

    _validate_k(k)

    relevant = _as_set(relevant_ids)

    if not relevant:
        return 0.0

    retrieved_top_k = _as_set(retrieved_ids[:k])

    return float(bool(retrieved_top_k & relevant))


# ---------------------------------------------------------
# RECALL AT K
# ---------------------------------------------------------

def recall_at_k(retrieved_ids, relevant_ids, k: int = 5) -> float:
    """
    Calculate the proportion of all relevant items found in top-k.
    """

    _validate_k(k)

    relevant = _as_set(relevant_ids)

    if not relevant:
        return 0.0

    retrieved_top_k = _as_set(retrieved_ids[:k])

    return len(retrieved_top_k & relevant) / len(relevant)


# ---------------------------------------------------------
# RECIPROCAL RANK
# ---------------------------------------------------------

def reciprocal_rank(retrieved_ids, relevant_ids) -> float:
    """
    Return the reciprocal rank of the first relevant result.

    Example:
        First relevant result at rank 2 -> reciprocal rank = 0.5.
        No relevant result -> reciprocal rank = 0.0.
    """

    relevant = _as_set(relevant_ids)

    if not relevant:
        return 0.0

    # Preserve ranking order when locating the first relevant result.
    for rank, item_id in enumerate(retrieved_ids, start=1):
        if item_id in relevant:
            return 1.0 / rank

    return 0.0


# ---------------------------------------------------------
# MEAN RECIPROCAL RANK
# ---------------------------------------------------------

def mean_reciprocal_rank(results) -> float:
    """
    Calculate the average reciprocal rank across multiple questions.

    Args:
        results: List of (retrieved_ids, relevant_ids) pairs.
    """

    if not results:
        return 0.0

    scores = [
        reciprocal_rank(retrieved, relevant)
        for retrieved, relevant in results
    ]

    return sum(scores) / len(scores)
