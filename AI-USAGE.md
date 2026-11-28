# AI Usage Policy and Disclosure

## 1. Purpose and Scope

This document distinguishes AI features provided by the application from AI
tools used to assist software development. It describes the implementation
verified in the source code and records where development-use information is
author-reported or unavailable. It does not claim that AI-generated content is
always accurate.

## 2. AI Features in the Application

The deployed API uses Google's Gemini services for document/query embeddings
and answer generation. The code defaults are:

| Purpose | Model ID | Use |
|---|---|---|
| Primary answer generation | `gemini-3.8-flash` | Produces a response from the question and retrieved document passages |
| Fallback answer generation | `gemini-3.5-flash-lite` | Tried after retryable API failures from the primary answer model |
| Document and query embeddings | `gemini-embedding-001` | Converts document chunks and user questions into 3072-dimensional vectors |

These model IDs can be overridden by runtime environment settings. The private
local environment and live deployment settings have not been inspected, so the
models active in a particular deployment are unverified.

The active API uses Gemini embeddings. The educational notebook
`notebooks/02_chunking_and_embeddings.ipynb` uses Sentence Transformers through
the legacy `EMBEDDING_MODEL` configuration, whose code default is
`sentence-transformers/all-MiniLM-L6-v2`. This notebook path is separate from
the current Gemini API path. The historical evaluation results also predate
the Gemini embedding migration and do not establish current Gemini quality.

## 3. How the RAG Feature Works

### Document ingestion

The service extracts text from supported documents and splits it into chunks
of 800 characters with 150 characters of overlap. It sends chunk text to
Gemini Embeddings with the `RETRIEVAL_DOCUMENT` task type, in batches of up to
64. The service validates that each returned vector has 3072 values.

Vectors and their text and metadata are stored in the Qdrant collection
`rag_documents_gemini_001`. The collection uses cosine similarity. Payload
metadata includes the document and user identifiers, filename, page, and chunk
position.

### Question retrieval and answer generation

1. The authenticated user's question is embedded using
   `gemini-embedding-001` with the `RETRIEVAL_QUERY` task type.
2. Qdrant searches by cosine similarity, restricted to that user's vectors and,
   when provided, the selected document IDs. The default result count is five
   chunks and the maximum is ten.
3. The application passes only chunks meeting the configured similarity
   threshold of 0.30 to answer generation. If none meet the threshold, the
   application abstains with a message that relevant information was not found.
4. Gemini Flash receives the question and retrieved passages. The system prompt
   instructs it to answer from those passages, avoid unsupported claims, and
   treat passage text as untrusted data rather than instructions. For a
   follow-up, recent chat history may help resolve references; the prompt says
   that history is not evidence.
5. If the primary answer model encounters a retryable API failure, the service
   tries Gemini Flash Lite. The fallback is for answer generation; it is not an
   alternate embedding model.
6. Citations are assembled separately by the application from the retrieved
   chunks' filename, page, chunk position, and similarity metadata. They are
   not generated or independently verified by Gemini.

The response evaluation code checks basic structure, such as a non-empty answer
and the presence of retrieved sources and citations. These checks do not
establish that an answer is factually or semantically supported.

## 4. Runtime Configuration and Data Handling

Relevant code defaults include a generation temperature of 0.1, a maximum of
512 output tokens, request pacing defaults of 60 embedding requests and 10
generation requests per minute, and up to two application retries for
retryable Gemini API errors. Provider retry hints and quotas may affect
availability; local pacing does not increase a provider's quota or coordinate
limits across multiple backend processes.

Document text is sent to Google's Gemini API to create embeddings. User
questions and retrieved passages are sent to Gemini for answer generation.
Users should follow their organization's privacy requirements and avoid
submitting material they are not authorized to process with these services.
This document does not reproduce credentials or secret environment values.

## 5. Limitations and Human Verification

- Generated answers can be incomplete, misleading, or factually wrong, even
  when the prompt requires grounding.
- Answer quality depends on the uploaded documents, text extraction, chunking,
  embedding quality, retrieval results, and selected similarity threshold.
  Relevant passages may be missed, and retrieved passages may not support the
  answer.
- A citation identifies retrieved source metadata; it does not prove that the
  cited passage entails every statement in the answer.
- Similarity thresholding and abstention reduce some unsupported responses but
  do not guarantee that all unsupported questions are rejected.
- Prompt-injection checks and prompt instructions are limited safeguards, not
  a comprehensive security control.
- Evaluation artifacts include historical results and a small manually
  verified retrieval subset; they do not prove current Gemini answer quality.

Users should check generated answers against the cited source documents and
seek qualified human review before relying on them, especially for academic,
professional, or high-impact decisions. The application is an information
retrieval aid, not a substitute for expert judgment.

## 6. AI Assistance During Software Development

Application runtime AI and development-time AI assistance are separate:

| Category | Disclosure | Verification status |
|---|---|---|
| Application runtime | Google Gemini models listed in Section 2 | Model defaults and call sites are in source; effective deployment overrides are unverified |
| Earlier development assistance | The previous version of this document reported use of ChatGPT for coding, debugging, explanations, documentation, and evaluation guidance | Author-reported; the repository does not establish exact model versions or which code was AI-generated |
| This documentation review | Copilot SDK in VS Code was used to inspect the implementation and prepare this disclosure | The specific underlying model/version and per-session settings are not available in the repository or current session record |
| Development environment | VS Code and Jupyter are listed in the previous disclosure | These are development tools, not by themselves AI models or proof of AI-generated work |

The repository does not contain a complete development prompt log or complete
chat transcripts. The prompt examples in the previous version of this file
were explicitly representative, not exhaustive, and cannot be verified against
an archived transcript here. This disclosure is therefore not a substitute for
the complete prompts and chat history. If an academic submission requires
those records, the project author should export them from the relevant AI
platforms and submit them separately rather than reconstructing or guessing
missing conversations.

No development-assistant model configuration or credentials are recorded here.
The exact model and configuration for earlier AI-assisted sessions remain
unverified.

## 7. Review and Responsibility

AI assistance is advisory. The project author remains responsible for reviewing
and validating code, documentation, evaluation methods, and submitted work.
Automated software tests can identify some implementation defects, but passing
tests do not establish the factual correctness of generated answers. Test
results should be reported with the relevant run and environment; this
documentation update does not report a new application test run.
