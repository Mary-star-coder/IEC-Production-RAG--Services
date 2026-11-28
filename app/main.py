
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIST, get_allowed_origins
from app.api.documents import router as documents_router
from app.api.questions import router as question_router
from app.api.auth import router as auth_router
from app.api.chats import router as chats_router


# ---------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("production_rag")


# ---------------------------------------------------------
# RATE LIMIT CONFIGURATION
# ---------------------------------------------------------

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60

# In-memory rate-limit storage:
# {client_ip: (window_start_time, request_count)}
_rate_limit_store = {}


# ---------------------------------------------------------
# FASTAPI APPLICATION INITIALIZATION
# ---------------------------------------------------------

app = FastAPI(
    title="Production RAG Service",
    description=(
        "Document-based question answering with retrieval, "
        "source citations, authentication and upload management."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS CONFIGURATION
# ---------------------------------------------------------

ALLOWED_ORIGINS = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Request-ID",
    ],
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "Retry-After",
    ],
)


# ---------------------------------------------------------
# REQUEST TRACKING, RATE LIMITING AND LOGGING
# ---------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    try:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = (
                request.client.host
                if request.client
                else "unknown"
            )

        current_time = time.monotonic()

        # Periodically clean expired rate-limit entries.
        # Cleanup is performed before adding new entries.
        if len(_rate_limit_store) > 10000:
            expired_clients = [
                ip
                for ip, (window_start, _) in _rate_limit_store.items()
                if (
                    current_time - window_start
                    >= RATE_LIMIT_WINDOW_SECONDS
                )
            ]

            for ip in expired_clients:
                _rate_limit_store.pop(ip, None)

        # Apply rate limiting to API routes.
        if request.url.path.startswith("/api/"):

            window_start, request_count = _rate_limit_store.get(
                client_ip,
                (current_time, 0),
            )

            # Reset expired rate-limit window.
            if (
                current_time - window_start
                >= RATE_LIMIT_WINDOW_SECONDS
            ):
                window_start = current_time
                request_count = 0

            # Reject requests after configured limit.
            if request_count >= RATE_LIMIT_REQUESTS:

                retry_after = max(
                    1,
                    int(
                        RATE_LIMIT_WINDOW_SECONDS
                        - (current_time - window_start)
                    ),
                )

                duration_ms = round(
                    (time.perf_counter() - start_time) * 1000,
                    2,
                )

                logger.warning(
                    "request_id=%s method=%s path=%s "
                    "status_code=429 client_ip=%s latency_ms=%s",
                    request_id,
                    request.method,
                    request.url.path,
                    client_ip,
                    duration_ms,
                )

                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            "Too many requests. "
                            "Please try again later."
                        ),
                        "request_id": request_id,
                    },
                    headers={
                        "X-Request-ID": request_id,
                        "X-RateLimit-Limit": str(
                            RATE_LIMIT_REQUESTS
                        ),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": str(retry_after),
                    },
                )

            # Count accepted request.
            request_count += 1

            _rate_limit_store[client_ip] = (
                window_start,
                request_count,
            )

        # Process request.
        response = await call_next(request)

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        response.headers["X-Request-ID"] = request_id

        if request.url.path.startswith("/api/"):

            response.headers["X-RateLimit-Limit"] = str(
                RATE_LIMIT_REQUESTS
            )

            current_count = _rate_limit_store.get(
                client_ip,
                (0, 0),
            )[1]

            remaining = max(
                0,
                RATE_LIMIT_REQUESTS - current_count,
            )

            response.headers["X-RateLimit-Remaining"] = str(
                remaining
            )

        logger.info(
            "request_id=%s method=%s path=%s "
            "status_code=%s latency_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response

    except Exception:
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            "request_id=%s method=%s path=%s "
            "status_code=500 latency_ms=%s",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )

        raise


# ---------------------------------------------------------
# API ROUTER REGISTRATION
# ---------------------------------------------------------

app.include_router(documents_router)
app.include_router(question_router)
app.include_router(auth_router)
app.include_router(chats_router)


# ---------------------------------------------------------
# ROOT ENDPOINT
# ---------------------------------------------------------

@app.get("/")
def root():
    """Serve the React app in production, or API status locally."""

    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    return {
        "message": "Production RAG Service is running.",
        "docs": "/docs",
    }


# ---------------------------------------------------------
# HEALTH CHECK ENDPOINT
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    """Return application health status for Render and local checks."""

    return {
        "status": "healthy",
    }


# ---------------------------------------------------------
# PRODUCTION FRONTEND (SPA)
# ---------------------------------------------------------

_RESERVED_PREFIXES = (
    "api/",
    "docs",
    "redoc",
    "openapi.json",
    "health",
)

_assets_dir = FRONTEND_DIST / "assets"
if _assets_dir.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=_assets_dir),
        name="frontend-assets",
    )


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    """Serve built frontend files and support React Router paths."""

    if full_path.startswith(_RESERVED_PREFIXES) or full_path in {
        "docs",
        "redoc",
        "openapi.json",
        "health",
    }:
        raise HTTPException(status_code=404, detail="Not Found")

    index_file = FRONTEND_DIST / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=404, detail="Not Found")

    candidate = FRONTEND_DIST / full_path
    if candidate.is_file() and candidate.resolve().is_relative_to(FRONTEND_DIST.resolve()):
        return FileResponse(candidate)

    return FileResponse(index_file)
