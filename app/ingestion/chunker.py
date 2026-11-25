
# ---------------------------------------------------------
# DOCUMENT TEXT CHUNKING
# ---------------------------------------------------------

def chunk_documents(
    pages: list[dict],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[dict]:
    """
    Split extracted document text into smaller overlapping chunks.

    Chunking makes long documents easier to process, embed,
    store, and search during retrieval.

    Original page numbers and chunk positions are preserved
    to support source citations.

    Args:
        pages: Extracted document pages with text and page numbers.
        chunk_size: Maximum number of characters in each chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        A list of dictionaries containing chunk text,
        original page number, and chunk position.

    Raises:
        ValueError: If chunk size or overlap settings are invalid.
    """

    # Chunk size must be a positive number.
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    # Overlap must be non-negative and smaller than chunk size.
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be non-negative and smaller than chunk_size."
        )

    # Store all generated chunks from the supplied document pages.
    chunks = []

    # Calculate the distance between consecutive chunk starting positions.
    # This creates overlapping chunks to preserve context.
    step = chunk_size - chunk_overlap

    # Process each extracted page separately.
    for page_data in pages:
        text = page_data["text"]
        page_number = page_data["page"]

        # Start extracting text from the beginning of the current page.
        start = 0

        # Continue until the complete page text has been processed.
        while start < len(text):
            # Extract a chunk using the configured maximum size.
            chunk_text = text[start:start + chunk_size].strip()

            # Ignore chunks that contain only whitespace.
            if chunk_text:
                chunks.append({
                    "text": chunk_text,

                    # Preserve the original page or slide number.
                    "page": page_number,

                    # Assign a sequential position to each generated chunk.
                    "position": len(chunks),
                })

            # Move forward while retaining the configured overlap.
            start += step

    # Return all generated chunks with their source metadata.
    return chunks
