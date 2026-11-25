
# Production RAG Service

A document-based Retrieval-Augmented Generation (RAG) application that allows users to upload documents, ask questions, retrieve relevant evidence, and receive source citations.

Built with FastAPI, React, ChromaDB, and Sentence Transformers.

## Project Overview

This project implements a code-based RAG pipeline for document question answering.

Users can upload supported documents, process their content into overlapping chunks, generate embeddings, store them in ChromaDB, and ask questions against the uploaded collection.

The system uses similarity-based retrieval and abstains when retrieved evidence does not meet the configured relevance threshold.

## Features

- PDF, DOCX, PPTX, TXT, and Markdown document support
- Document text extraction and chunking
- Sentence Transformer embeddings
- Persistent ChromaDB vector storage
- Semantic similarity retrieval
- Source citations and retrieved chunk inspection
- Similarity-based abstention
- SHA-256 duplicate detection
- Document listing and deletion
- React frontend
- 25-question golden evaluation dataset
- Retrieval metric calculations
- Chunking and similarity threshold experiments
- Request ID and latency logging
- API documentation through Swagger

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.11, FastAPI |
| Frontend | React, Vite |
| Vector database | ChromaDB |
| Embedding model | all-MiniLM-L6-v2 |
| Document processing | PyPDF, python-docx, python-pptx |
| Evaluation | Python-based evaluation framework |
| Testing | Pytest |

## Architecture

1. User uploads a document through the React interface.
2. FastAPI validates the file and checks its SHA-256 hash.
3. The document loader extracts text and metadata.
4. The chunker creates overlapping text segments.
5. Sentence Transformers generates embeddings.
6. ChromaDB stores vectors and metadata.
7. User submits a question.
8. The system retrieves the top relevant chunks.
9. Similarity threshold filtering determines whether sufficient evidence exists.
10. The application returns an extractive answer, citations, and retrieved evidence, or abstains.

See [DESIGN.md](DESIGN.md) for architecture and design decisions.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Mary-star-coder/IEC-Production-RAG--Services.git
cd IEC-Production-RAG--Services
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the backend

```bash
uvicorn app.main:app --reload
```

Backend:
`http://127.0.0.1:8000`

Swagger documentation:
`http://127.0.0.1:8000/docs`

Health endpoint:
`http://127.0.0.1:8000/health`

### 5. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite.

## Document Corpus

The original evaluation documents are not included in this repository.

Provide your own permitted PDF, DOCX, PPTX, TXT, or Markdown documents through the application upload interface.

The configured maximum upload size is 15 MB per file.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/documents/upload` | Upload and index a document |
| GET | `/api/documents/` | List uploaded documents |
| DELETE | `/api/documents/{document_id}` | Delete a document |
| POST | `/api/questions/ask` | Ask a question |

## Evaluation

The evaluation dataset contains 25 questions:

- 20 answerable questions
- 5 unanswerable questions

The project compares two chunking configurations and evaluates different similarity thresholds.

Retrieval metrics include:

- Hit Rate@K
- Recall@K
- Mean Reciprocal Rank (MRR)

Retrieval relevance was manually verified for five questions. The reported retrieval metrics therefore represent this verified subset, not all 25 questions.

The evaluation also records abstention behavior and the trade-off between rejecting unsupported questions and incorrectly rejecting answerable questions.

See [EVAL.md](EVAL.md) for detailed results and limitations.

## Tests

The project test suite was previously executed successfully:

```text
30 passed
```

Run the tests with:

```bash
python -m pytest -v
```

## Screenshots

Project interface and evaluation screenshots are available in the `screenshots/` directory.

## Current Limitations

- Answers are extractive and use retrieved document text rather than LLM-generated responses.
- Authentication is a demonstration implementation, not production JWT authentication.
- Per-user document isolation is not implemented.
- Prompt-injection detection uses known phrase patterns and is not comprehensive.
- Retrieval metrics are manually verified on a limited five-question subset.
- Similarity-based abstention requires further validation.
- Production rate limiting, service-unavailable handling, and timeout/retry policies require further hardening.

## Future Improvements

- Secure JWT authentication and user-level document isolation
- Grounded LLM-based answer generation
- Stronger prompt-injection and document-level security
- Expanded retrieval and answer-quality evaluation
- Rate limiting and resilient service handling
- Monitoring and production deployment

## AI Usage

See [AI-USAGE.md](AI-USAGE.md) for documentation of AI assistance used during development.

## Author

Mary

## License

No open-source redistribution license is currently specified. Review third-party dependencies and document ownership before redistributing this project.
```
