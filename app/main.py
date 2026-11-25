
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.questions import router as question_router


# ---------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("production_rag")


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
# REQUEST TRACKING AND LOGGING
# ---------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    try:
        response = await call_next(request)

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        response.headers["X-Request-ID"] = request_id

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
            (time.perf_counter() - start_time) * 1000, 2
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
