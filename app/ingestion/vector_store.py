
# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

import logging
from typing import Any

import chromadb

from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction,
)

from app.config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
)

from app.exceptions import ServiceUnavailableError


# ---------------------------------------------------------
# LOGGER CONFIGURATION
# ---------------------------------------------------------

logger = logging.getLogger("production_rag.vector_store")


# ---------------------------------------------------------
# VECTOR DATABASE INITIALIZATION
# ---------------------------------------------------------

try:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    embedding_function = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_function,
    )

    logger.info(
        "ChromaDB initialized successfully: collection=%s",
        COLLECTION_NAME,
    )

except Exception as exc:
    logger.exception("Failed to initialize ChromaDB.")

    raise ServiceUnavailableError(
        "Vector database initialization failed."
    ) from exc


# ---------------------------------------------------------
# ADD DOCUMENT CHUNKS
# ---------------------------------------------------------

def add_chunks(
    document_id: str,
    filename: str,
    chunks: list[dict[str, Any]],
    user_id: str = "legacy",
) -> int:
    """
    Store document chunks with user ownership metadata.

    Args:
        document_id: Unique document identifier.
        filename: Original document filename.
        chunks: Extracted document chunks.
        user_id: Owner of the uploaded document.

    Returns:
        Number of stored chunks.
    """

    if not chunks:
        raise ValueError("No chunks provided.")

    if not user_id:
        raise ValueError("user_id cannot be empty.")

    ids = []
    documents = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        ids.append(f"{document_id}_{index}")
        documents.append(chunk["text"])

        metadatas.append({
            "document_id": document_id,
            "filename": filename,
            "page": chunk["page"],
            "position": chunk["position"],
            "user_id": str(user_id),
        })

    try:
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "Document chunks stored: document_id=%s user_id=%s count=%s",
            document_id,
            user_id,
            len(ids),
        )

        return len(ids)

    except Exception as exc:
        logger.exception(
            "Failed to add document chunks: document_id=%s",
            document_id,
        )

        raise ServiceUnavailableError(
            "Document storage is temporarily unavailable."
        ) from exc


# ---------------------------------------------------------
# SEARCH DOCUMENT CHUNKS
# ---------------------------------------------------------

def search_chunks(
    query: str,
    top_k: int = 5,
    user_id: str = "legacy",
) -> list[dict[str, Any]]:
    """
    Retrieve relevant chunks belonging only to the specified user.

    Args:
        query: User's search question.
        top_k: Maximum number of chunks to retrieve.
        user_id: Owner whose documents may be searched.

    Returns:
        Retrieved chunks with metadata and similarity scores.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty.")

    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    if not user_id:
        raise ValueError("user_id cannot be empty.")

    try:
        user_filter = {
            "user_id": str(user_id)
        }

        # Count this user's chunks using collection.get().
        # This is compatible with ChromaDB versions where
        # collection.count() does not accept a where argument.
        user_documents = collection.get(
            where=user_filter,
            include=[],
        )

        total_chunks = len(user_documents["ids"])

        if total_chunks == 0:
            logger.info(
                "No document chunks found for user_id=%s",
                user_id,
            )
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, total_chunks),
            where=user_filter,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        matches = []

        for text, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            similarity = max(
                0.0,
                min(1.0, 1.0 - distance),
            )

            matches.append({
                "text": text,
                "metadata": metadata,
                "distance": distance,
                "similarity": similarity,
            })

        logger.info(
            "Vector search completed: user_id=%s retrieved_count=%s",
            user_id,
            len(matches),
        )

        return matches

    except Exception as exc:
        logger.exception(
            "Failed to search ChromaDB for user_id=%s",
            user_id,
        )

        raise ServiceUnavailableError(
            "Document retrieval is temporarily unavailable."
        ) from exc


# ---------------------------------------------------------
# DELETE DOCUMENT VECTORS
# ---------------------------------------------------------

def delete_document(
    document_id: str,
    user_id: str | None = None,
) -> None:
    """
    Delete document vectors, optionally restricted to their owner.

    Args:
        document_id: Unique document identifier.
        user_id: If supplied, restrict deletion to this owner.
    """

    try:
        if user_id is None:
            delete_filter = {
                "document_id": document_id
            }
        else:
            delete_filter = {
                "$and": [
                    {"document_id": document_id},
                    {"user_id": str(user_id)},
                ]
            }

        collection.delete(
            where=delete_filter
        )

        logger.info(
            "Document vectors deleted: document_id=%s user_id=%s",
            document_id,
            user_id if user_id is not None else "all",
        )

    except Exception as exc:
        logger.exception(
            "Failed to delete document vectors: document_id=%s",
            document_id,
        )

        raise ServiceUnavailableError(
            "Document storage is temporarily unavailable."
        ) from exc


# ---------------------------------------------------------
# COLLECTION COUNT
# ---------------------------------------------------------

def get_collection_count(
    user_id: str | None = None,
) -> int:
    """
    Return the total chunk count, optionally for one user.

    Args:
        user_id: Optional owner filter.

    Returns:
        Number of stored chunks.
    """

    try:
        if user_id is None:
            return collection.count()

        # Use collection.get() for compatibility with ChromaDB.
        user_documents = collection.get(
            where={"user_id": str(user_id)},
            include=[],
        )

        return len(user_documents["ids"])

    except Exception as exc:
        logger.exception(
            "Failed to count document chunks."
        )

        raise ServiceUnavailableError(
            "Document storage is temporarily unavailable."
        ) from exc
