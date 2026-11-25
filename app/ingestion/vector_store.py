
# ChromaDB provides persistent vector storage and similarity search.
import chromadb

# Import the Sentence Transformer embedding function.
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Import vector database and embedding configuration settings.
from app.config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL


# ---------------------------------------------------------
# VECTOR DATABASE INITIALIZATION
# ---------------------------------------------------------

# Create the persistent database directory if it does not exist.
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Initialize a persistent ChromaDB client.
# Stored embeddings remain available across application restarts.
client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

# Initialize the embedding model used to convert text into vectors.
embedding_function = SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

# Retrieve the existing collection or create it if necessary.
# Cosine distance is used to measure vector similarity.
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
    embedding_function=embedding_function,
)


# ---------------------------------------------------------
# ADD DOCUMENT CHUNKS
# ---------------------------------------------------------

def add_chunks(document_id, filename, chunks):
    """
    Store document chunks and their metadata in ChromaDB.

    Each chunk receives a unique ID based on its document ID
    and position within the document.

    Args:
        document_id: Unique identifier of the source document.
        filename: Original uploaded document filename.
        chunks: Extracted and processed text chunks.

    Returns:
        Number of chunks successfully submitted for storage.

    Raises:
        ValueError: If no chunks are provided.
    """

    # Prevent insertion of an empty chunk collection.
    if not chunks:
        raise ValueError("No chunks provided.")

    # Prepare separate lists required by the ChromaDB add operation.
    ids = []
    documents = []
    metadatas = []

    # Process each chunk and assign a unique identifier.
    for index, chunk in enumerate(chunks):
        ids.append(f"{document_id}_{index}")
        documents.append(chunk["text"])

        # Preserve source information for retrieval and citations.
        metadatas.append({
            "document_id": document_id,
            "filename": filename,
            "page": chunk["page"],
            "position": chunk["position"],
        })

    # Add documents and metadata to the persistent vector collection.
    # ChromaDB automatically creates embeddings using the configured model.
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    # Return the number of inserted chunk IDs.
    return len(ids)


# ---------------------------------------------------------
# SEARCH RELEVANT DOCUMENT CHUNKS
# ---------------------------------------------------------

def search_chunks(query, top_k=5):
    """
    Search the vector database for chunks relevant to a query.

    Args:
        query: User question or search text.
        top_k: Maximum number of matching chunks to return.

    Returns:
        A list of matching chunks containing text, metadata,
        vector distance, and calculated similarity scores.

    Raises:
        ValueError: If the query is empty or top_k is invalid.
    """

    # Reject empty search queries.
    if not query.strip():
        raise ValueError("Query cannot be empty.")

    # Ensure the requested result count is positive.
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    # Check how many chunks are currently stored in the collection.
    total_chunks = collection.count()

    # Return an empty list if no documents have been indexed.
    if total_chunks == 0:
        return []

    # Query ChromaDB using the text embedding and cosine distance.
    # Avoid requesting more results than the collection contains.
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, total_chunks),
        include=["documents", "metadatas", "distances"],
    )

    # Prepare a structured list of retrieval results.
    matches = []

    # Combine retrieved text, metadata, and distance information.
    for text, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        matches.append({
            "text": text,
            "metadata": metadata,
            "distance": distance,

            # Convert cosine distance into a bounded similarity score.
            "similarity": max(0.0, min(1.0, 1.0 - distance)),
        })

    return matches


# ---------------------------------------------------------
# DELETE DOCUMENT VECTORS
# ---------------------------------------------------------

def delete_document(document_id):
    """
    Remove all stored chunks belonging to a specific document.

    The document ID metadata filter ensures that only the
    selected document's vectors are deleted.
    """

    collection.delete(
        where={"document_id": document_id}
    )


# ---------------------------------------------------------
# COLLECTION STATISTICS
# ---------------------------------------------------------

def get_collection_count():
    """
    Return the total number of chunks stored in ChromaDB.
    """
    return collection.count()
