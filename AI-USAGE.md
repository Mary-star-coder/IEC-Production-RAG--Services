# AI Usage Documentation

## 1. Purpose of AI Assistance

AI tools were used as development assistants during the implementation of the Production RAG Service portfolio project.

AI assistance supported code development, debugging, documentation, evaluation design, and project organization.

The final implementation was reviewed, executed, and tested locally.

## 2. AI Tools Used

| Tool | Purpose |
|---|---|
| ChatGPT | Coding assistance, debugging, explanations, documentation, and evaluation guidance |
| Visual Studio Code | Code editing and project development |
| Jupyter Notebook | Running and documenting ingestion, chunking, embedding, and evaluation experiments |

**Note:** ChatGPT was used as a development assistant. The RAG application itself uses Sentence Transformers embeddings and extractive answer generation.

## 3. Areas Where AI Assistance Was Used

### Project Architecture
- Discussing the RAG application architecture.
- Organizing the FastAPI backend and React frontend.
- Separating ingestion, retrieval, generation, evaluation, and guardrail modules.

### Document Ingestion
- Assistance with PDF, DOCX, PPTX, and text document extraction.
- Designing document metadata and chunking workflows.
- Debugging document processing issues.

### Chunking and Embeddings
- Comparing chunk sizes and overlap settings.
- Understanding embedding dimensions and vector storage.
- Designing experiments for 800/150 and 500/100 configurations.

### Retrieval and Answer Generation
- Implementing retrieval workflows using ChromaDB.
- Supporting similarity-based filtering and abstention.
- Generating extractive answers with source citations.

### Guardrails
- Implementing basic input validation.
- Adding checks for suspicious prompt-injection phrases.
- Supporting abstention when relevant context is insufficient.

### Evaluation
- Preparing a 25-question golden dataset.
- Implementing retrieval metrics such as Hit Rate@5, Recall@5, and MRR.
- Running similarity threshold experiments.
- Comparing chunking configurations.
- Documenting evaluation limitations.

### Testing and Debugging
- Assistance with pytest debugging.
- Reviewing API behavior and error handling.
- Running and reviewing the project's automated tests.

### Documentation
- Preparing and improving README.md.
- Documenting architecture and technical decisions in DESIGN.md.
- Recording evaluation methodology and results in EVAL.md.
- Preparing this AI usage document.

## 4. Example Prompts Used

The following are representative examples of prompts used during development, not a complete verbatim conversation history.

1. "Help me design a production-style RAG service using FastAPI and ChromaDB."

2. "Help me implement document ingestion for PDF and DOCX files with metadata."

3. "Explain how to implement chunking with configurable chunk size and overlap."

4. "Help me evaluate retrieval using Hit Rate@K, Recall@K, and MRR."

5. "Help me implement similarity threshold-based abstention."

6. "Review my FastAPI code and help debug failing pytest tests."

7. "Help me compare two chunking configurations using reproducible evaluation results."

8. "Review my project documentation against the instructor's requirements."

## 5. Human Review and Verification

AI-generated suggestions were not treated as automatically correct.

The following verification steps were performed:

- Code was reviewed and integrated into the project.
- Python modules were executed locally.
- Jupyter notebooks were executed and saved with outputs.
- Evaluation scripts were run locally.
- Automated tests were executed, with 30 tests passing in the recorded test run.
- Evaluation results were saved as JSON files.
- Documentation was updated to reflect observed results and known limitations.

## 6. Models and Configuration

The RAG application uses:

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding dimensions: 384
- Vector database: ChromaDB
- Backend framework: FastAPI
- Answer generation approach: Extractive answer generation

ChatGPT was used for development assistance. The exact ChatGPT model/version used during every development session should be confirmed from the available conversation or account records rather than assumed.

## 7. Limitations and Transparency

- AI assistance does not replace human verification.
- Evaluation results are limited by the manually verified question subset.
- Chunking comparison uses page-level relevance mapping as a proxy.
- The current frontend demo authentication is not a production JWT authentication system.
- Basic prompt-injection checks are not a complete security solution.
- The application uses extractive generation rather than a hosted generative LLM.

## 8. Conclusion

AI tools supported the development and documentation of this project. The implementation, experiments, and test results were reviewed through local execution.

The project author remains responsible for the final code, design decisions, evaluation results, and submitted deliverables.