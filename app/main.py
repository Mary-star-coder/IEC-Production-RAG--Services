
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.documents import router as documents_router
from app.api.questions import router as question_router
from app.api.auth import router as auth_router

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
    description="Document-based question answering with retrieval and citations.",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS CONFIGURATION
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# REQUEST TRACKING, RATE LIMITING AND LOGGING
# ---------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    try:
        # Identify the client using its direct connection IP.
        client_ip = (
            request.client.host
            if request.client
            else "unknown"
        )

        current_time = time.monotonic()

        # Apply rate limiting to API routes.
        if request.url.path.startswith("/api/"):

            window_start, request_count = _rate_limit_store.get(
                client_ip,
                (current_time, 0),
            )

            # Start a fresh window when the previous one expires.
            if current_time - window_start >= RATE_LIMIT_WINDOW_SECONDS:
                window_start = current_time
                request_count = 0

            # Reject requests after the configured limit.
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
                        "detail": "Too many requests. Please try again later.",
                        "request_id": request_id,
                    },
                    headers={
                        "X-Request-ID": request_id,
                        "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": str(retry_after),
                    },
                )

            # Count the accepted request.
            request_count += 1

            _rate_limit_store[client_ip] = (
                window_start,
                request_count,
            )

            # Periodically remove expired client entries.
            if len(_rate_limit_store) > 10000:
                expired_clients = [
                    ip
                    for ip, (start, _) in _rate_limit_store.items()
                    if current_time - start >= RATE_LIMIT_WINDOW_SECONDS
                ]

                for ip in expired_clients:
                    _rate_limit_store.pop(ip, None)

        # Continue normal request processing.
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

            remaining = max(
                0,
                RATE_LIMIT_REQUESTS
                - _rate_limit_store.get(client_ip, (0, 0))[1],
            )

            response.headers["X-RateLimit-Remaining"] = str(remaining)

        logger.info(
            "request_id=%s method=%s path=%s status_code=%s latency_ms=%s",
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
            "request_id=%s method=%s path=%s status_code=500 latency_ms=%s",
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


# ---------------------------------------------------------
# ROOT ENDPOINT
# ---------------------------------------------------------

@app.get("/")
def root():
    """Return API status and Swagger documentation location."""
    return {
        "message": "Production RAG Service is running.",
        "docs": "/docs",
    }


# ---------------------------------------------------------
# HEALTH CHECK ENDPOINT
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    """Return application health status."""
    return {"status": "healthy"}
