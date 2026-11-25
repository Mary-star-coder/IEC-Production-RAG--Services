
# Import the vector database search function.
from app.ingestion.vector_store import search_chunks

# Import the default number of chunks to retrieve.
from app.config import DEFAULT_TOP_K


def retrieve_relevant_chunks(question: str, top_k: int = DEFAULT_TOP_K):
    """
    Retrieve the most relevant document chunks for a user question.

    The question is validated and cleaned before being passed
    to the vector database search function.

    Args:
        question: User's natural language question.
        top_k: Maximum number of relevant chunks to retrieve.

    Returns:
        A list of matching document chunks with metadata
        and similarity scores.

    Raises:
        ValueError: If the question is empty or contains only whitespace.
    """

    # Prevent database searches using empty questions.
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    # Remove unnecessary whitespace and retrieve relevant chunks.
    return search_chunks(question.strip(), top_k=top_k)
