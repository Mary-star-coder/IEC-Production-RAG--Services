
def generate_citations(retrieved_chunks: list[dict]) -> list[dict]:
    """
    Generate citations from the metadata of retrieved chunks.

    Each citation contains the filename, page, chunk position,
    and similarity score of its source passage.
    """

    citations = []
    seen = set()

    for chunk in retrieved_chunks:
        if not isinstance(chunk, dict):
            continue

        metadata = chunk.get("metadata") or {}

        # Skip chunks without enough source information.
        filename = metadata.get("filename")
        page = metadata.get("page")
        position = metadata.get("position")

        if filename is None or page is None or position is None:
            continue

        # Avoid duplicate citations for the same source chunk.
        citation_key = (filename, page, position)

        if citation_key in seen:
            continue

        seen.add(citation_key)

        try:
            similarity = float(chunk.get("similarity", 0.0))
        except (TypeError, ValueError):
            similarity = 0.0

        # Keep similarity scores within the documented range.
        similarity = max(0.0, min(1.0, similarity))

        citations.append({
            "filename": str(filename),
            "page": int(page),
            "position": int(position),
            "similarity": round(similarity, 4),
        })

    return citations
