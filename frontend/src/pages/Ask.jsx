import { useState } from "react";
import { apiRequest } from "../lib/api";
import "./Pages.css";

export default function Ask() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function askQuestion(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await apiRequest("/api/questions/ask", {
        method: "POST",
        body: JSON.stringify({ question: question.trim(), top_k: 5 }),
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <p className="eyebrow">DOCUMENT INTELLIGENCE</p>
      <h1>Ask your documents</h1>
      <p className="muted">Ask a question and inspect the retrieved evidence behind the response.</p>
      <form className="content-card question-card" onSubmit={askQuestion}>
        <label htmlFor="question-input">Your question</label>
        <textarea id="question-input" rows="4" value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Example: What is machine learning?" minLength={3} maxLength={1000} required />
        <div className="question-footer">
          <small>{question.length}/1000 characters Â· Top 5 results</small>
          <button className="primary-button" disabled={loading}>{loading ? "Searching..." : "Search documents â†’"}</button>
        </div>
      </form>
      {error && <div className="notice error-notice">{error}</div>}
      {result && (
        <div className="results-area">
          <div className="content-card">
            <div className="result-heading">
              <h2>Answer</h2>
              <span className={result.abstained ? "result-status abstained" : "result-status"}>
                {result.abstained ? "No supporting evidence" : "Retrieved from documents"}
              </span>
            </div>
            <p className="answer-text">{result.answer}</p>
          </div>
          <div className="content-card">
            <h2>Source citations</h2>
            {!result.citations?.length ? <p className="muted">No citations available for this question.</p> :
              result.citations.map((citation, index) => (
                <div className="citation-row" key={index}>
                  <strong>{citation.filename}</strong>
                  <span>Page: {citation.page ?? "N/A"}</span>
                  <span>Position: {citation.position ?? "N/A"}</span>
                  <span>Similarity: {citation.similarity}</span>
                </div>
              ))}
          </div>
          <div className="content-card">
            <h2>Retrieved chunks ({result.retrieved_count ?? result.retrieved_chunks?.length ?? 0})</h2>
            {!result.retrieved_chunks?.length ? <p className="muted">No chunks retrieved.</p> :
              result.retrieved_chunks.map((chunk, index) => (
                <details className="chunk-item" key={index}>
                  <summary>Chunk {index + 1} Â· {chunk.metadata?.filename} Â· Similarity: {Number(chunk.similarity || 0).toFixed(3)}</summary>
                  <p>{chunk.text}</p>
                </details>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
