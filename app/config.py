
import os
from pathlib import Path


# ---------------------------------------------------------
# PROJECT DIRECTORY CONFIGURATION
# ---------------------------------------------------------

# Resolve the project root directory from the current file location.
BASE_DIR = Path(__file__).resolve().parent.parent

# Directory used to store uploaded source documents.
UPLOAD_DIR = BASE_DIR / "uploads"

# Persistent storage directory for the ChromaDB vector database.
CHROMA_DIR = BASE_DIR / "chroma_db"


# ---------------------------------------------------------
# DOCUMENT UPLOAD SETTINGS
# ---------------------------------------------------------

# Maximum permitted upload size: 15 MB.
MAX_FILE_SIZE = 15 * 1024 * 1024

# File formats supported by the document ingestion pipeline.
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}


# ---------------------------------------------------------
# RETRIEVAL AND VECTOR DATABASE SETTINGS
# ---------------------------------------------------------

# Name of the ChromaDB collection used to store document chunks.
COLLECTION_NAME = "rag_documents_st"

# Sentence Transformer model used to convert text into embeddings.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Default number of relevant chunks returned during retrieval.
DEFAULT_TOP_K = 5

# Minimum similarity score required for accepting retrieved results.
SIMILARITY_THRESHOLD = 0.30


# ---------------------------------------------------------
# TEXT CHUNKING SETTINGS
# ---------------------------------------------------------

# Maximum character length of each document chunk.
CHUNK_SIZE = 800

# Number of overlapping characters between consecutive chunks.
# Overlap helps preserve context across chunk boundaries.
CHUNK_OVERLAP = 150

# In-memory per-client rate limiting.
RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60


# ---------------------------------------------------------
# JWT AUTHENTICATION CONFIGURATION
# ---------------------------------------------------------

# Secret key is provided through an environment variable.
# Never hardcode the real secret key in source code.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")

# Algorithm used to sign and verify JWT access tokens.
JWT_ALGORITHM = "HS256"

# Access token validity period in minutes.
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# SQLite database used to store registered user accounts.
AUTH_DATABASE_PATH = BASE_DIR / "auth_users.db"
