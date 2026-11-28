
# Production RAG Service

A document-based Retrieval-Augmented Generation (RAG) application that allows users to upload documents, ask questions, retrieve relevant evidence, and receive source citations.

Built with FastAPI, React, Gemini, Qdrant, and Supabase.

## Project Overview

This project implements a code-based RAG pipeline for document question answering.

Users can upload supported documents, process their content into overlapping chunks, generate embeddings, store them in Qdrant, and ask questions against the uploaded collection.

The system uses similarity-based retrieval and abstains when retrieved evidence does not meet the configured relevance threshold.

## Features

- PDF, DOCX, PPTX, TXT, and Markdown document support
- Document text extraction and chunking
- Gemini embeddings (`gemini-embedding-001`) and grounded answer generation
- Automatic fallback to a configurable Gemini model for transient generation errors
- Qdrant Cloud vector storage (embedded Qdrant for local development)
- Supabase Auth, RLS-protected Postgres document metadata, and private Storage
- Supabase-backed per-user chat history, follow-up context, and per-turn document source selection
- Email-based Supabase password recovery
- Duplicate detection across Supabase metadata and Qdrant vectors
- Per-user, top-k answer caching in Supabase, invalidated when documents change
- Search scoped to selected documents
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
| Vector database | Qdrant |
| Embedding model | Gemini `gemini-embedding-001` |
| Document processing | PyPDF, python-docx, python-pptx |
| Evaluation | Python-based evaluation framework |
| Testing | Pytest |

## Architecture

1. User uploads a document through the React interface.
2. FastAPI validates the file and checks its SHA-256 hash.
3. The document loader extracts text and metadata.
4. The chunker creates overlapping text segments.
5. Gemini generates per-chunk embeddings.
6. Qdrant stores vectors and metadata.
7. Supabase Storage keeps the original file and Postgres records its metadata.
8. User submits a question.
9. Gemini embeds the query; Qdrant retrieves only that user's relevant chunks.
10. Similarity threshold filtering determines whether sufficient evidence exists.
11. Gemini answers from the retrieved passages and the API returns source citations, or abstains.

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

Create `.env` from `.env.example` and fill in the Gemini and Supabase
credentials. Set Qdrant Cloud values if you want to use the hosted collection;
otherwise local development uses embedded Qdrant.

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

The Vite dev server proxies `/api` and `/health` to FastAPI, so you do not need `VITE_API_URL` locally.

Local development uses embedded Qdrant when `QDRANT_URL` is blank. To use
Qdrant Cloud locally, set `QDRANT_URL` and `QDRANT_API_KEY` in `.env`.
Configure `GEMINI_API_KEY`, `SUPABASE_URL`, and
`SUPABASE_PUBLISHABLE_KEY` as well. Run [`supabase/schema.sql`](supabase/schema.sql)
in the Supabase SQL Editor to create the RLS-protected metadata and chat tables
and private document bucket. For an existing project that already has the
document schema, run
[`supabase/chat_history_migration.sql`](supabase/chat_history_migration.sql)
in the SQL Editor to add chat history without rerunning the full schema.
Supabase Auth email-confirmation settings determine whether new users receive
an immediate session or must confirm their email first.
If you change `SUPABASE_STORAGE_BUCKET`, update the matching bucket ID in that
SQL setup file too.

The Gemini collection is versioned separately from the earlier
Sentence Transformer collection. Existing vectors are not converted; documents
must be uploaded again after configuring Gemini.

## Render Deployment

This service is set up as a **single Docker web service**: FastAPI serves the API and the built React app on the same origin.

### Deploy on the Free instance

1. Push this repository to GitHub (the folder that contains `Dockerfile` and `app/`).
2. In Render: **New → Web Service →** connect the repo.
3. Runtime: **Docker**. Instance type: **Free**. Health check path: `/health`.
4. Set the following values in Render's environment settings:

| Variable | Required | Value |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Gemini API key; configure it as a secret |
| `GEMINI_MODEL` | No | Defaults to `gemini-3.8-flash` |
| `GEMINI_FALLBACK_MODEL` | No | Defaults to `gemini-3.5-flash-lite`; used for transient primary-model errors |
| `GEMINI_EMBEDDING_MODEL` | No | Defaults to `gemini-embedding-001` |
| `QDRANT_URL` | Yes | Qdrant Cloud cluster endpoint |
| `QDRANT_API_KEY` | Yes | Qdrant Cloud API key; configure it as a secret |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Supabase publishable key; configure it as a secret |
| `SUPABASE_PASSWORD_RESET_REDIRECT_URL` | No | Password reset page; defaults to `FRONTEND_URL`, Render's service URL, or local Vite |
| `SUPABASE_STORAGE_BUCKET` | No | Defaults to `documents` |
| `ENVIRONMENT` | Yes | `production` |

5. Apply [`supabase/schema.sql`](supabase/schema.sql) to the Supabase project
   before accepting uploads. It creates the document, question-cache, and chat
   tables, cache invalidation triggers, a private bucket, and user-scoped RLS policies.
   The app uses user access tokens and the publishable key; do not place a
   Supabase service-role key in the Render environment.
6. In Supabase Authentication URL Configuration, set the Site URL to the
   deployed Render origin and add the exact
   `SUPABASE_PASSWORD_RESET_REDIRECT_URL` value to the allowed redirect URLs.
   For local development, allow `http://localhost:5173/reset-password` and set
   that URL in `.env`. On Render, the app defaults to the service URL plus
   `/reset-password`; set the variable to override it.

You can also use the Blueprint file `render.yaml` (**New → Blueprint**).

Render Free instances spin down after 15 minutes without inbound traffic,
have a 750 instance-hour monthly limit, and use an ephemeral filesystem. The first
request after spin-down can be delayed. This application keeps documents and
metadata in Supabase and vectors in Qdrant Cloud, so local disk persistence is
not required. Gemini and the hosted services remain separately subject to
their own quotas and billing.

After deploy:

- App: `https://<service>.onrender.com`
- Health: `https://<service>.onrender.com/health`
- Swagger: `https://<service>.onrender.com/docs`

The first boot connects to Qdrant Cloud and creates the versioned 3072-dimension
Gemini collection if needed. Existing 384-dimension Sentence Transformer vectors
are not compatible and must be re-indexed.

### Native Python runtime (alternative)

If you do not use Docker:

- Build: `pip install -r requirements-prod.txt && cd frontend && npm ci && npm run build`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips='*'`

Node.js must be available in that environment so the frontend can build.

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
| GET, POST | `/api/chats/` | List or create chat sessions |
| GET | `/api/chats/{chat_id}` | Load a chat and its saved turns |
| DELETE | `/api/chats/{chat_id}` | Delete a chat and its history |

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

Run the tests with:

```bash
python -m pytest -v
```

## Screenshots

Project interface and evaluation screenshots are available in the `screenshots/` directory.

## Current Limitations

- The grounded prompt and citations do not guarantee that generated answers are semantically faithful.
- Prompt-injection detection uses known phrase patterns and is not comprehensive.
- Retrieval metrics are manually verified on a limited five-question subset and predate the Gemini migration.
- Similarity-based abstention requires calibration with the selected Gemini embedding model.
- Render Free instances sleep when idle and have limited monthly hours; hosted services have their own quotas.

## Future Improvements

- Stronger prompt-injection and document-level security
- Expanded retrieval and semantic answer-quality evaluation
- Rate limiting and resilient service handling
- Monitoring and production deployment

## AI Usage

See [AI-USAGE.md](AI-USAGE.md) for documentation of AI assistance used during development.

## Author

Mary

## License

No open-source redistribution license is currently specified. Review third-party dependencies and document ownership before redistributing this project.
```
