
# System Design — Production RAG Service

## 1. Overview

The Production RAG Service is a document question-answering application built using a code-based Retrieval-Augmented Generation architecture.

The system processes uploaded documents, converts their text into embeddings, stores those embeddings in a persistent vector database, and retrieves relevant evidence in response to user questions.

The application prioritizes traceability by returning source citations and retrieved chunks. It abstains when retrieved evidence does not meet the configured similarity threshold.

## 2. Technology Choices

| Component | Selected Technology | Reason |
|---|---|---|
| Backend | FastAPI | Typed request validation, API documentation, and Python integration |
| Frontend | React and Vite | Interactive document and question-answering interface |
| Embeddings | all-MiniLM-L6-v2 | Compact sentence embedding model with relatively low inference cost |
| Vector database | ChromaDB | Persistent local vector storage and metadata filtering |
| PDF extraction | PyPDF | Python-based PDF text extraction |
| DOCX extraction | python-docx | Word document text extraction |
| PPTX extraction | python-pptx | Presentation text extraction |
| Testing | Pytest | Automated API and component tests |

## 3. System Architecture

The application contains four major layers:

1. React frontend
2. FastAPI API layer
3. Document ingestion and retrieval pipeline
4. ChromaDB vector storage

### Request flow

```text
User
 |
 v
React Frontend
 |
 v
FastAPI Backend
 |
 +--------------------------+
 |                          |
 v                          v
Document Upload         Question API
 |                          |
 v                          v
Text Extraction         Query Embedding
 |                          |
 v                          v
Text Chunking           ChromaDB Search
 |                          |
 v                          v
Embedding Generation    Similarity Filtering
 |                          |
 v                          v
ChromaDB Storage        Extractive Answer
                            |
                            v
                      Citations and Evaluation
                            |
                            v
                       React Frontend
```

## 4. Document Ingestion

The ingestion pipeline performs the following steps:

1. Validate the file extension.
2. Read the uploaded file.
3. Enforce the 15 MB maximum file size.
4. Calculate the SHA-256 hash.
5. Reject duplicate file content.
6. Generate a unique document ID.
7. Extract text and source metadata.
8. Split text into overlapping chunks.
9. Generate embeddings.
10. Store vectors and metadata in ChromaDB.
11. Save the document record in the JSON registry.

Supported formats:

- PDF
- DOCX
- PPTX
- TXT
- Markdown

The system preserves document identifiers, filenames, page or slide information, and chunk positions as metadata.

## 5. Chunking Strategy

The default configuration is:

- Chunk size: 800 characters
- Chunk overlap: 150 characters

Overlap preserves context across chunk boundaries. Larger chunks can retain more surrounding information, while smaller chunks can provide more precise retrieval units.

Two configurations were experimentally compared:

| Metric | Configuration A | Configuration B |
|---|---:|---:|
| Chunk size | 800 | 500 |
| Overlap | 150 | 100 |
| Total chunks | 863 | 1,313 |
| Hit Rate@5 | 100% | 100% |
| Recall@5 | 100% | 90% |
| MRR | 0.6667 | 0.7067 |
| Average retrieval latency | 0.0208 sec | 0.1265 sec |

Configuration A was selected as the provisional default because it achieved full recall on the verified subset and lower measured retrieval latency.

Configuration B achieved a higher MRR, indicating better average ranking position, but lower recall in this experiment.

These results are based on a limited manually verified subset and a single latency measurement run. They should not be treated as universal performance guarantees.

## 6. Embedding Model Selection

Selected model:

`sentence-transformers/all-MiniLM-L6-v2`

Reasons:

- Compact model size
- 384-dimensional embeddings
- Suitable for semantic similarity search
- Lower computational requirements than many larger embedding models

Alternatives include larger Sentence Transformer models and hosted embedding APIs.

Larger models may improve semantic representation but generally increase compute requirements, memory use, and inference cost.

Hosted embedding APIs can reduce local infrastructure requirements but introduce network dependency, external service cost, and data privacy considerations.

The selected model provides a practical local baseline for this portfolio project.

## 7. Vector Database Selection

Selected vector database: ChromaDB.

Reasons:

- Persistent local storage
- Simple Python integration
- Metadata support
- Similarity search
- Suitable for local development and portfolio demonstration

Alternatives:

- FAISS: efficient vector similarity search, but persistence and metadata management require additional application code.
- Pinecone: managed vector database with hosted infrastructure, but introduces external service dependency and operational cost.

ChromaDB was selected to keep the project reproducible and locally executable without requiring a hosted vector database account.

## 8. Retrieval Strategy

The retrieval pipeline:

1. Converts the question into an embedding.
2. Searches ChromaDB for the top K similar chunks.
3. Uses a default top K value of 5.
4. Converts vector distance into a similarity score.
5. Filters results using a configured threshold of 0.30.
6. Abstains if no retrieved chunk meets the threshold.

The threshold is a configurable experimental value, not a universally calibrated relevance score.

A lower threshold can increase recall but may admit irrelevant evidence. A higher threshold can reduce unsupported answers but may reject valid questions.

The threshold experiments are documented in EVAL.md.

## 9. Answer Generation and Grounding

The current implementation uses extractive answer generation.

It constructs responses from retrieved document text and creates citations from retrieved chunk metadata.

This design avoids introducing a generative model that could produce unsupported information.

A future LLM-based implementation could produce more fluent synthesized answers, but would require additional prompt design, grounding validation, token-cost management, and answer faithfulness evaluation.

The current implementation should therefore be understood as an extractive RAG baseline rather than a fully generative RAG system.

## 10. Guardrails and Validation

The application implements:

- Empty question rejection
- Question length validation
- Basic known prompt-injection phrase detection
- File extension validation
- File size validation
- SHA-256 duplicate detection
- Similarity-based abstention
- Source citations from retrieved evidence
- Generic error messages for unexpected processing failures

The prompt-injection filter uses known phrase patterns. It is not a complete defense against indirect prompt injection, adversarial documents, or novel jailbreak techniques.

Authentication and user-level document isolation are not production-ready.

## 11. API Error Handling

The API uses structured HTTP responses.

| Status | Intended use |
|---|---|
| 200 | Successful retrieval or question response |
| 201 | Document uploaded |
| 204 | Document deleted |
| 400 | Invalid question or empty file |
| 404 | Document not found |
| 409 | Duplicate document |
| 415 | Unsupported file format |
| 422 | Request schema validation failure |
| 413 | Upload exceeds configured size |
| 500 | Unexpected processing failure |

Rate limiting and explicit service-unavailable responses require additional implementation before production deployment.

## 12. Logging and Observability

The backend includes request tracking middleware.

It records:

- Unique request ID
- HTTP method
- Request path
- Response status code
- Request processing latency

The request ID is also returned through the `X-Request-ID` response header.

Document and question processing operations log successful actions and unexpected errors.

Sensitive document contents, API keys, and user secrets should not be written to logs.

Centralized monitoring, metrics dashboards, and distributed tracing are future improvements.

## 13. Evaluation Framework

The evaluation framework uses a manually curated golden dataset of 25 questions.

Dataset composition:

- 20 answerable questions
- 5 unanswerable questions

Retrieval metrics:

- Hit Rate@K
- Recall@K
- Mean Reciprocal Rank

The manually verified retrieval relevance subset currently contains five questions.

Threshold experiments evaluate the balance between false abstentions and accepting unanswerable questions.

The framework also compares two chunking configurations.

Faithfulness and correctness require further independent evaluation. Current automated answer checks should not be interpreted as a complete semantic quality judge.

See EVAL.md for results, experimental details, and limitations.

## 14. Reliability and Performance Trade-offs

The implementation uses asynchronous file reading in the upload endpoint and synchronous document processing and vector operations.

This keeps the code straightforward but does not provide complete non-blocking processing for expensive embedding and document extraction operations.

The current service has request ID and latency logging, generic error responses, and basic exception handling.

Additional production hardening should include:

- Explicit request and processing timeouts
- Retry policies for transient external service failures
- Rate limiting
- Service health and dependency checks
- Background processing for large ingestion jobs
- Centralized monitoring and alerting
- Secure authentication and access control

Retries should only be introduced for operations that are safe to repeat and for failures known to be transient.

## 15. Current Limitations

- Extractive answers rather than LLM-generated synthesis
- Basic phrase-based prompt-injection detection
- Demo authentication rather than production JWT
- No per-user document isolation
- Limited manually verified retrieval dataset
- No comprehensive semantic faithfulness evaluation
- No complete rate-limiting or retry implementation
- Local ChromaDB deployment rather than managed production infrastructure

## 16. Future Improvements

- Grounded LLM-based answer generation
- Secure JWT authentication
- Per-user document isolation
- Stronger prompt-injection defenses
- Expanded golden evaluation dataset
- Semantic answer-quality evaluation
- Rate limiting and resilient timeout/retry handling
- Centralized monitoring and production deployment
