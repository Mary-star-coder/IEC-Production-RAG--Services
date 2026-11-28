
import logging
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from app.config import (
    COLLECTION_NAME,
    ENVIRONMENT,
    QDRANT_API_KEY,
    QDRANT_LOCAL_DIR,
    QDRANT_URL,
    VECTOR_SIZE,
)
from app.exceptions import ServiceUnavailableError
from app.gemini import embed_texts


logger = logging.getLogger("production_rag.vector_store")

MAX_TOP_K = 10


try:
    if ENVIRONMENT == "test":
        client = QdrantClient(":memory:")
    elif QDRANT_URL:
        if not QDRANT_API_KEY:
            raise ValueError(
                "QDRANT_API_KEY is required when QDRANT_URL is configured."
            )
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
        )
    elif ENVIRONMENT == "production":
        raise ValueError(
            "QDRANT_URL and QDRANT_API_KEY must be configured in production."
        )
    else:
        QDRANT_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=str(QDRANT_LOCAL_DIR))

    if not VECTOR_SIZE:
        raise ValueError(
            "The configured Gemini embedding size is invalid."
        )

    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )

    if QDRANT_URL:
        for field_name in ("document_id", "user_id", "file_hash"):
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
                wait=True,
            )

    logger.info("Qdrant initialized: collection=%s", COLLECTION_NAME)

except Exception as exc:
    logger.exception("Qdrant initialization failed.")

    raise ServiceUnavailableError(
        "Vector database initialization failed."
    ) from exc


def point_id(chunk_id: str) -> str:
    """Convert the existing string chunk ID into a stable Qdrant UUID."""

    return str(uuid5(NAMESPACE_URL, f"production-rag:{chunk_id}"))


def add_chunks(
    document_id: str,
    filename: str,
    chunks: list[dict[str, Any]],
    user_id: str = "legacy",
    file_hash: str | None = None,
) -> int:
    """
    Store document chunks with document and user metadata.

    The legacy user_id default is retained for notebook compatibility.
    Authenticated API routes should always pass the actual user ID.
    """

    if not document_id or not filename or not user_id:
        raise ValueError(
            "document_id, filename, and user_id are required."
        )

    if not chunks:
        raise ValueError("No document chunks were provided.")

    point_payloads = []
    chunk_ids = []

    for index, chunk in enumerate(chunks):
        text = chunk.get("text")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Chunk at position {index} contains no usable text."
            )

        try:
            page = int(chunk["page"])
            position = int(chunk["position"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Chunk at position {index} has invalid metadata."
            ) from exc

        if page < 1 or position < 0:
            raise ValueError(
                f"Chunk at position {index} has invalid page or position."
            )

        chunk_id = f"{document_id}_{index}"
        chunk_ids.append(chunk_id)
        point_payloads.append({
            "chunk_id": chunk_id,
            "text": text.strip(),
            "document_id": str(document_id),
            "filename": str(filename),
            "page": page,
            "position": position,
            "user_id": str(user_id),
            **({"file_hash": file_hash} if file_hash else {}),
        })

    try:
        vectors = embed_texts(
            [payload["text"] for payload in point_payloads],
            task_type="RETRIEVAL_DOCUMENT",
        )
        if len(vectors) != len(point_payloads):
            raise ValueError(
                "The embedding model returned an invalid vector count."
            )

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=point_id(chunk_id),
                    vector=vector,
                    payload=payload,
                )
                for chunk_id, vector, payload in zip(
                    chunk_ids,
                    vectors,
                    point_payloads,
                )
            ],
            wait=True,
        )

        logger.info(
            "Stored document chunks: document_id=%s user_id=%s count=%s",
            document_id,
            user_id,
            len(chunk_ids),
        )

        return len(chunk_ids)

    except Exception as exc:
        logger.exception(
            "Failed to store chunks for document_id=%s",
            document_id,
        )

        raise ServiceUnavailableError(
            "Document storage is temporarily unavailable."
        ) from exc


def document_exists(file_hash: str, user_id: str) -> bool:
    """Check whether Qdrant already contains this user's document hash."""

    if not isinstance(file_hash, str) or not file_hash.strip():
        raise ValueError("file_hash cannot be empty.")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id cannot be empty.")

    try:
        result = client.count(
            collection_name=COLLECTION_NAME,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    ),
                    models.FieldCondition(
                        key="file_hash",
                        match=models.MatchValue(value=file_hash),
                    ),
                ]
            ),
            exact=True,
        )
        return result.count > 0
    except Exception as exc:
        logger.exception(
            "Qdrant duplicate lookup failed for user_id=%s",
            user_id,
        )
        raise ServiceUnavailableError(
            "Document storage is temporarily unavailable."
        ) from exc


def search_chunks(
    query: str,
    top_k: int = 5,
    user_id: str = "legacy",
    document_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant chunks for one user.

    Qdrant's cosine score is returned as similarity, with distance retained
    for compatibility with the existing retrieval response shape.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty.")

    # Reject invalid types and non-positive values with the exact
    # error message expected by the existing tests.
    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        raise ValueError("top_k must be greater than zero.")

    # Enforce the maximum retrieval limit separately.
    if top_k > MAX_TOP_K:
        raise ValueError(
            f"top_k cannot exceed {MAX_TOP_K}."
        )

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id cannot be empty.")
    if document_ids is not None and any(
        not isinstance(document_id, str) or not document_id.strip()
        for document_id in document_ids
    ):
        raise ValueError("document_ids must contain non-empty strings.")
    if document_ids is not None and not document_ids:
        return []

    try:
        conditions = [
            models.FieldCondition(
                key="user_id",
                match=models.MatchValue(value=str(user_id)),
            )
        ]
        if document_ids is not None:
            conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(
                        any=list(dict.fromkeys(document_ids)),
                    ),
                )
            )
        user_filter = models.Filter(must=conditions)

        query_vector = embed_texts(
            [query.strip()],
            task_type="RETRIEVAL_QUERY",
        )[0]

        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=user_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

        matches = []

        for point in results.points:
            payload = point.payload or {}
            text = payload.get("text")

            if not isinstance(text, str) or not text:
                continue

            score = float(point.score)
            similarity = max(
                0.0,
                min(1.0, score),
            )
            metadata = {
                key: value
                for key, value in payload.items()
                if key not in {"chunk_id", "text"}
            }

            matches.append({
                "text": text,
                "metadata": metadata,
                "distance": 1.0 - score,
                "similarity": similarity,
            })

        logger.info(
            "Search completed: user_id=%s retrieved=%s",
            user_id,
            len(matches),
        )

        return matches

    except ServiceUnavailableError:
        raise

    except Exception as exc:
        logger.exception(
            "Vector search failed for user_id=%s",
            user_id,
        )

        raise ServiceUnavailableError(
            "Document retrieval is temporarily unavailable."
        ) from exc


def delete_document(
    document_id: str,
    user_id: str | None = None,
) -> None:
    """
    Delete all vectors belonging to a document.

    When user_id is supplied, deletion is restricted to that owner.
    """

    if not document_id:
        raise ValueError("document_id is required.")

    try:
        conditions = [
            models.FieldCondition(
                key="document_id",
                match=models.MatchValue(value=str(document_id)),
            )
        ]
        if user_id is not None:
            conditions.append(
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=str(user_id)),
                )
            )

        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=conditions)
            ),
            wait=True,
        )

        logger.info(
            "Deleted document vectors: document_id=%s user_id=%s",
            document_id,
            user_id if user_id is not None else "all",
        )

    except Exception as exc:
        logger.exception(
            "Vector deletion failed for document_id=%s",
            document_id,
        )

        raise ServiceUnavailableError(
            "Document storage is temporarily unavailable."
        ) from exc


def get_collection_count(
    user_id: str | None = None,
) -> int:
    """Return total chunk count, optionally filtered by user."""

    try:
        count_filter = None
        if user_id is not None:
            count_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=str(user_id)),
                    )
                ]
            )

        count = client.count(
            collection_name=COLLECTION_NAME,
            count_filter=count_filter,
            exact=True,
        )

        return count.count

    except Exception as exc:
        logger.exception("Failed to count vector records.")

        raise ServiceUnavailableError(
            "Document storage is temporarily unavailable."
        ) from exc
