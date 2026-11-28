
import os
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------
# PROJECT DIRECTORY CONFIGURATION
# ---------------------------------------------------------

# Resolve the project root directory from the current file location.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the .env file in the project root.
# This must happen before reading environment-backed settings below.
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()


def _data_dir() -> Path:
    """Return writable storage for embedded Qdrant in local development."""

    configured = os.getenv("DATA_DIR", "").strip()
    if configured:
        return Path(configured)

    # Render persistent disks are commonly mounted at /data.
    render_disk = Path("/data")
    if render_disk.is_dir() and os.access(render_disk, os.W_OK):
        return render_disk

    return BASE_DIR


DATA_DIR = _data_dir()
QDRANT_LOCAL_DIR = DATA_DIR / "qdrant_db"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

MAX_FILE_SIZE = 15 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}

QDRANT_URL = os.getenv("QDRANT_URL", "").strip()
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "").strip()

# Gemini vectors use a different size and collection than the earlier
# Sentence Transformer vectors.
COLLECTION_NAME = "rag_documents_gemini_001"
VECTOR_SIZE = 3072

# Retained for the local educational notebooks; the API uses Gemini.
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

DEFAULT_TOP_K = 5
SIMILARITY_THRESHOLD = 0.30
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = (
    os.getenv("GEMINI_MODEL", "").strip()
    or "gemini-3.8-flash"
)
GEMINI_FALLBACK_MODEL = (
    os.getenv("GEMINI_FALLBACK_MODEL", "").strip()
    or "gemini-3.5-flash-lite"
)
GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "",
).strip() or "gemini-embedding-001"

SUPABASE_URL = (
    os.getenv("SUPABASE_URL", "").strip()
    or os.getenv("VITE_SUPABASE_URL", "").strip()
).rstrip("/")
SUPABASE_PUBLISHABLE_KEY = (
    os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    or os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY", "").strip()
)
SUPABASE_PASSWORD_RESET_REDIRECT_URL = os.getenv(
    "SUPABASE_PASSWORD_RESET_REDIRECT_URL",
    "",
).strip()
if not SUPABASE_PASSWORD_RESET_REDIRECT_URL:
    _frontend_url = os.getenv("FRONTEND_URL", "").split(",", maxsplit=1)[0].strip()
    _render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
    _reset_base_url = (_frontend_url or _render_url).rstrip("/")
    if _reset_base_url:
        SUPABASE_PASSWORD_RESET_REDIRECT_URL = (
            f"{_reset_base_url}/reset-password"
        )
    elif ENVIRONMENT != "production":
        SUPABASE_PASSWORD_RESET_REDIRECT_URL = (
            "http://localhost:5173/reset-password"
        )
SUPABASE_STORAGE_BUCKET = os.getenv(
    "SUPABASE_STORAGE_BUCKET",
    "",
).strip() or "documents"

if ENVIRONMENT == "production":
    _missing_settings = [
        name
        for name, value in (
            ("GEMINI_API_KEY", GEMINI_API_KEY),
            ("QDRANT_URL", QDRANT_URL),
            ("QDRANT_API_KEY", QDRANT_API_KEY),
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_PUBLISHABLE_KEY", SUPABASE_PUBLISHABLE_KEY),
        )
        if not value
    ]
    if _missing_settings:
        raise RuntimeError(
            "Required production settings are missing: "
            + ", ".join(_missing_settings)
        )


def _split_origins(raw: str) -> list[str]:
    origins = []
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if origin:
            origins.append(origin)
    return origins


def get_allowed_origins() -> list[str]:
    """CORS origins for local Vite, optional split frontends, and Render."""

    origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5173",
        "https://marymoto-iec-production-rag-frontend.static.hf.space",
    ]

    origins.extend(_split_origins(os.getenv("FRONTEND_URL", "")))
    origins.extend(_split_origins(os.getenv("ALLOWED_ORIGINS", "")))

    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if render_url:
        origins.append(render_url)

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(origins))
