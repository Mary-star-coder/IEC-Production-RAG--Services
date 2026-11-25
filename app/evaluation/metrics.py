
def hit_rate_at_k(retrieved_ids, relevant_ids, k=5):
    """
    Check whether at least one relevant item appears in the top-k results.

    Returns:
        1.0 if a relevant item is found, otherwise 0.0.
    """
    # If there are no relevant items, return 0.0.
    if not relevant_ids:
        return 0.0

    # Consider only the first k retrieved items.
    retrieved_top_k = retrieved_ids[:k]

    # Check whether retrieved and relevant IDs have any overlap.
    return float(bool(set(retrieved_top_k) & set(relevant_ids)))


def recall_at_k(retrieved_ids, relevant_ids, k=5):
    """
    Calculate the fraction of all relevant items found in the top-k results.

    Returns:
        A value between 0.0 and 1.0.
    """
    # If there are no relevant items, return 0.0.
    if not relevant_ids:
        return 0.0

    # Convert the top-k retrieved IDs into a set for comparison.
    retrieved_top_k = set(retrieved_ids[:k])

    # Convert relevant IDs into a set to avoid duplicate counting.
    relevant = set(relevant_ids)

    # Divide the number of relevant items retrieved by total relevant items.
    return len(retrieved_top_k & relevant) / len(relevant)


def reciprocal_rank(retrieved_ids, relevant_ids):
    """
    Calculate the reciprocal rank of the first relevant retrieved item.

    Returns:
        1 / rank of the first relevant item, or 0.0 if none is found.
    """
    # Convert relevant IDs into a set for efficient membership checks.
    relevant = set(relevant_ids)

    # Return 0.0 if no relevant items are available.
    if not relevant:
        return 0.0

    # Enumerate retrieved items starting from rank 1.
    for rank, item_id in enumerate(retrieved_ids, start=1):

        # Check whether the current retrieved item is relevant.
        if item_id in relevant:

            # Return the reciprocal of the first relevant item's rank.
            return 1.0 / rank

    # Return 0.0 if no relevant item was retrieved.
    return 0.0


def mean_reciprocal_rank(results):
    """
    Calculate Mean Reciprocal Rank (MRR) across multiple queries.

    Args:
        results: List of (retrieved_ids, relevant_ids) pairs.

    Returns:
        Average reciprocal rank across all queries.
    """
    # Return 0.0 when there are no query results to evaluate.
    if not results:
        return 0.0

    # Calculate the reciprocal rank separately for each query.
    scores = [
        reciprocal_rank(retrieved, relevant)
        for retrieved, relevant in results
    ]

    # Return the average reciprocal rank across all queries.
    return sum(scores) / len(scores)
