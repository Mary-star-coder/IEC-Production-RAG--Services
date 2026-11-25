
import { useState } from "react";
import "./Pages.css";

// Backend API base URL used for document question requests.
const API = "";

// Render the question-answering page and display retrieved evidence.
export default function Ask() {
  // Store the user's question and the API response.
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);

  // Track request progress and any errors returned by the API.
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Send the question to the backend and retrieve relevant document chunks.
  async function askQuestion(e) {
    e.preventDefault();

    // Reset previous results and prepare the interface for a new request.
    setLoading(true);
    setError("");
    setResult(null);

    try {
      // Send the question and requested number of results to the FastAPI endpoint.
      const res = await fetch(`${API}/api/questions/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 5 }),
      });

      // Parse the JSON response returned by the backend.
      const data = await res.json();

      // Convert unsuccessful HTTP responses into readable errors.
      if (!res.ok) throw new Error(data.detail || "Question request failed.");

      // Store the answer, citations, and retrieved chunks for display.
      setResult(data);
    } catch (err) {
      // Display an error if the request fails or the backend is unavailable.
      setError(err.message);
    } finally {
      // Always stop the loading indicator after the request finishes.
      setLoading(false);
    }
  }

  return (
    <div className="page">
      {/* Introduce the document question-answering section. */}
      <p className="eyebrow">DOCUMENT INTELLIGENCE</p>
      <h1>Ask your documents</h1>
      <p className="muted">Ask a question and explore the retrieved evidence behind the response.</p>

      {/* Collect the user's question and submit it to the backend. */}
      <form className="content-card question-card" onSubmit={askQuestion}>
        <label htmlFor="question-input">Your question</label>
        <textarea
          id="question-input"
          rows="4"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Example: What is machine learning?"
          minLength={3}
          maxLength={1000}
          required
        />
        <div className="question-footer">
          {/* Show the question character count and retrieval limit. */}
          <small>{question.length}/1000 characters · Top 5 results</small>
          <button className="primary-button" disabled={loading}>
            {loading ? "Searching..." : "Search documents →"}
          </button>
        </div>
      </form>

      {/* Display API or network errors when a request fails. */}
      {error && <div className="notice error-notice">{error}</div>}

      {/* Render the answer and supporting evidence after a successful request. */}
      {result && (
        <div className="results-area">
          {/* Display the generated extractive answer and abstention status. */}
          <div className="content-card">
            <div className="result-heading">
              <h2>Answer</h2>
              <span className={result.abstained ? "result-status abstained" : "result-status"}>
                {result.abstained ? "No supporting evidence" : "Retrieved from documents"}
              </span>
            </div>
            <p className="answer-text">{result.answer}</p>
          </div>

          {/* Display source information associated with the answer. */}
          <div className="content-card">
            <h2>Source citations</h2>
            {!result.citations?.length ? (
              <p className="muted">No citations available for this question.</p>
            ) : (
              result.citations.map((citation, index) => (
                <div className="citation-row" key={index}>
                  <strong>{citation.filename}</strong>
                  <span>Page: {citation.page ?? "N/A"}</span>
                  <span>Position: {citation.position ?? "N/A"}</span>
                  <span>Similarity: {citation.similarity}</span>
                </div>
              ))
            )}
          </div>

          {/* Show the number and content of chunks retrieved by the RAG system. */}
          <div className="content-card">
            <h2>Retrieved chunks ({result.retrieved_count ?? 0})</h2>
            {!result.retrieved_chunks?.length ? (
              <p className="muted">No chunks retrieved.</p>
            ) : (
              result.retrieved_chunks.map((chunk, index) => (
                <details className="chunk-item" key={index}>
                  {/* Each chunk can be expanded to inspect its retrieved text. */}
                  <summary>
                    Chunk {index + 1} · {chunk.metadata?.filename}
                    {" · "}Similarity: {Number(chunk.similarity || 0).toFixed(3)}
                  </summary>
                  <p>{chunk.text}</p>
                </details>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
