
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# QUESTION REQUEST SCHEMA
# ---------------------------------------------------------

class QuestionRequest(BaseModel):
    # User's question with minimum and maximum length validation.
    question: str = Field(min_length=3, max_length=1000)

    # Number of relevant chunks to retrieve from the vector database.
    # Default is 5, with an allowed range of 1 to 10.
    top_k: int = Field(default=5, ge=1, le=10)


# ---------------------------------------------------------
# CITATION SCHEMA
# ---------------------------------------------------------

class Citation(BaseModel):
    # Name of the source document used to generate the answer.
    filename: str

    # Original page number containing the retrieved information.
    page: int

    # Position of the chunk within the document.
    position: int

    # Similarity score indicating relevance to the user's question.
    similarity: float


# ---------------------------------------------------------
# RETRIEVED CHUNK METADATA SCHEMA
# ---------------------------------------------------------

class ChunkMetadata(BaseModel):
    # Unique identifier of the source document.
    # Optional to support chunks where document ID is unavailable.
    document_id: str | None = None

    # Original source document filename.
    filename: str

    # Page or slide number from which the chunk was extracted.
    page: int

    # Position of the chunk in the processed document.
    position: int


class RetrievedChunk(BaseModel):
    # Text content retrieved from the vector database.
    text: str

    # Source information associated with the retrieved chunk.
    metadata: ChunkMetadata

    # Raw vector database distance score.
    distance: float

    # Converted similarity score used to assess relevance.
    similarity: float


# ---------------------------------------------------------
# ANSWER EVALUATION SCHEMA
# ---------------------------------------------------------

class AnswerEvaluation(BaseModel):
    # Indicates whether the answer passed the evaluation checks.
    passed: bool

    # Stores individual evaluation check results.
    checks: dict

    # Identifies the evaluation approach used.
    evaluation_type: str


# ---------------------------------------------------------
# QUESTION RESPONSE SCHEMA
# ---------------------------------------------------------

class QuestionResponse(BaseModel):
    # Final answer returned to the user.
    answer: str

    # Source citations supporting the answer.
    citations: list[Citation]

    # Chunks retrieved from the vector database.
    retrieved_chunks: list[RetrievedChunk]

    # Total number of chunks retrieved.
    retrieved_count: int

    # Indicates whether the system abstained from answering.
    abstained: bool

    # Evaluation details for the generated answer.
    answer_evaluation: AnswerEvaluation


# ---------------------------------------------------------
# DOCUMENT RESPONSE SCHEMAS
# ---------------------------------------------------------

class DocumentRecord(BaseModel):
    # Unique identifier assigned to an uploaded document.
    document_id: str

    # Original uploaded filename.
    filename: str

    # SHA-256 hash used for duplicate document detection.
    file_hash: str

    # Uploaded document size in bytes.
    file_size: int

    # Number of text chunks created from the document.
    chunk_count: int

    # Document extension or file format.
    file_type: str


class DocumentUploadResponse(BaseModel):
    # Confirmation message returned after document upload.
    message: str

    # Unique identifier of the uploaded document.
    document_id: str

    # Original filename.
    filename: str

    # SHA-256 hash of the uploaded file.
    file_hash: str

    # Size of the uploaded file in bytes.
    file_size: int

    # Number of chunks stored in the vector database.
    chunk_count: int

    # Uploaded document format.
    file_type: str


class DocumentListResponse(BaseModel):
    # Collection of uploaded document records.
    documents: list[DocumentRecord]


class DocumentDeleteResponse(BaseModel):
    # Confirmation message returned after document deletion.
    message: str
