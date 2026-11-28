
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------
# QUESTION REQUEST SCHEMA
# ---------------------------------------------------------

class QuestionRequest(BaseModel):
    """Validate a question submitted to the RAG service."""

    # Maximum question length is 1000 characters.
    # Keep this consistent with MAX_QUESTION_LENGTH in guardrails.py.
    question: str = Field(
        min_length=3,
        max_length=1000,
        description="Question to answer using the user's uploaded documents.",
        examples=["What are the main concepts discussed in the document?"],
    )

    # Restrict retrieval size to prevent unnecessarily expensive searches.
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of document chunks to retrieve.",
    )
    document_ids: list[UUID] | None = Field(
        default=None,
        max_length=1000,
        description="Optional document IDs to restrict retrieval to.",
    )
    chat_id: UUID | None = Field(
        default=None,
        description="Chat session to append this question and answer to.",
    )


class ChatSessionCreateRequest(BaseModel):
    """Validate a new chat session title."""

    title: str = Field(default="New chat", min_length=1, max_length=80)


# ---------------------------------------------------------
# CITATION SCHEMA
# ---------------------------------------------------------

class Citation(BaseModel):
    """Identify the source passage used in an answer."""

    filename: str = Field(description="Original source filename.")
    page: int = Field(ge=1, description="Original page or slide number.")
    position: int = Field(ge=0, description="Chunk position in the document.")
    similarity: float = Field(
        ge=0.0,
        le=1.0,
        description="Cosine similarity score between 0 and 1.",
    )


# ---------------------------------------------------------
# RETRIEVED CHUNK SCHEMAS
# ---------------------------------------------------------

class ChunkMetadata(BaseModel):
    """Metadata identifying the origin of a retrieved chunk."""

    document_id: str | None = None
    filename: str
    page: int = Field(ge=1)
    position: int = Field(ge=0)


class RetrievedChunk(BaseModel):
    """A retrieved source passage and its relevance scores."""

    text: str
    metadata: ChunkMetadata
    distance: float
    similarity: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------
# ANSWER EVALUATION SCHEMA
# ---------------------------------------------------------

class AnswerEvaluation(BaseModel):
    """Represent the result of answer-grounding checks."""

    passed: bool
    checks: dict[str, bool | str | int | float]
    evaluation_type: str


# ---------------------------------------------------------
# QUESTION RESPONSE SCHEMA
# ---------------------------------------------------------

class QuestionResponse(BaseModel):
    """Response containing the answer and its retrieval evidence."""

    answer: str
    citations: list[Citation]
    retrieved_chunks: list[RetrievedChunk]
    retrieved_count: int = Field(ge=0)
    abstained: bool
    answer_evaluation: AnswerEvaluation


# ---------------------------------------------------------
# DOCUMENT RESPONSE SCHEMAS
# ---------------------------------------------------------

class DocumentRecord(BaseModel):
    """Safe document information returned by the document API."""

    document_id: str
    filename: str
    file_hash: str
    file_size: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    file_type: str


class DocumentUploadResponse(BaseModel):
    """Confirmation returned after a successful document upload."""

    message: str
    document_id: str
    filename: str
    file_hash: str
    file_size: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    file_type: str


class DocumentListResponse(BaseModel):
    """List of documents belonging to the authenticated user."""

    documents: list[DocumentRecord]


class DocumentDeleteResponse(BaseModel):
    """Confirmation returned after document deletion."""

    message: str


# ---------------------------------------------------------
# AUTHENTICATION REQUEST AND RESPONSE SCHEMAS
# ---------------------------------------------------------

class UserRegisterRequest(BaseModel):
    """Validate user registration information."""

    email: str = Field(
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="A valid email address.",
    )

    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password containing at least 8 characters.",
    )


class UserLoginRequest(BaseModel):
    """Validate user login credentials."""

    email: str = Field(
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class TokenResponse(BaseModel):
    """Return the Supabase session tokens after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class RefreshRequest(BaseModel):
    """Validate a Supabase refresh token."""

    refresh_token: str = Field(min_length=1)


class PasswordResetRequest(BaseModel):
    """Validate an email address for password recovery."""

    email: str = Field(
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )


class PasswordUpdateRequest(BaseModel):
    """Validate a new password submitted from a recovery session."""

    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Return safe registration information and optional session tokens."""

    user_id: str
    email: str
    access_token: str | None = None
    refresh_token: str | None = None
    requires_email_confirmation: bool = False
