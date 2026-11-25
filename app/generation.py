
# ---------------------------------------------------------
# EXTRACTIVE ANSWER GENERATION
# ---------------------------------------------------------

def generate_extractive_answer(retrieved_chunks):
    """
    Generate an answer using only the text of retrieved document chunks.

    This implementation follows an extractive RAG approach:
    it combines relevant source passages instead of generating
    new information using a language model.

    Args:
        retrieved_chunks: List of chunks returned by retrieval.

    Returns:
        Combined source text, or an empty string if no usable
        chunks are available.
    """

    # Return an empty answer when retrieval produces no results.
    if not retrieved_chunks:
        return ""

    # Combine non-empty retrieved passages into a single answer.
    return "\n\n".join(
        chunk["text"].strip()
        for chunk in retrieved_chunks
        if chunk.get("text", "").strip()
    )


# ---------------------------------------------------------
# CITATION GENERATION
# ---------------------------------------------------------

def generate_citations(retrieved_chunks):
    """
    Create source citations from retrieved chunk metadata.

    Each citation identifies the source filename, page number,
    chunk position, and similarity score.

    Args:
        retrieved_chunks: List of retrieved document chunks.

    Returns:
        A list of citation dictionaries.
    """

    # Initialize an empty list to store generated citations.
    citations = []

    # Process each retrieved chunk to extract its source information.
    for chunk in retrieved_chunks:
        metadata = chunk["metadata"]

        # Build a citation using the original document metadata.
        citations.append({
            "filename": metadata["filename"],
            "page": metadata["page"],
            "position": metadata["position"],
            "similarity": round(chunk["similarity"], 4),
        })

    # Return all citations associated with the retrieved chunks.
    return citations
