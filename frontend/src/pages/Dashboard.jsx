
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import "./Pages.css";

// Backend API base URL for retrieving uploaded documents.
const API = "http://127.0.0.1:8000";

// Display workspace statistics, quick actions, and recent documents.
export default function Dashboard() {
  // Store the documents retrieved from the backend.
  const [documents, setDocuments] = useState([]);

  // Track the connection status of the FastAPI backend.
  const [apiStatus, setApiStatus] = useState("Checking...");

  // Fetch document information when the dashboard first loads.
  useEffect(() => {
    fetch(`${API}/api/documents/`)
      .then((res) => {
        // Treat unsuccessful HTTP responses as API errors.
        if (!res.ok) throw new Error("API error");
        return res.json();
      })
      .then((data) => {
        // Support both a direct document list and a wrapped API response.
        setDocuments(Array.isArray(data) ? data : data.documents || []);
        setApiStatus("Connected");
      })
      .catch(() => {
        // Show a disconnected status if the backend request fails.
        setApiStatus("Not connected");
      });
  }, []);

  // Calculate the total number of indexed chunks across all documents.
  const totalChunks = documents.reduce(
    (sum, doc) => sum + (doc.chunk_count || 0), 0
  );

  return (
    <div className="page">
      {/* Display the workspace introduction and document upload shortcut. */}
      <div className="welcome-row">
        <div>
          <p className="eyebrow">OVERVIEW</p>
          <h1>Welcome to your workspace ✨</h1>
          <p className="muted">Manage documents and get answers from your knowledge base.</p>
        </div>
        <Link className="primary-link" to="/documents">+ Upload document</Link>
      </div>

      {/* Display key workspace statistics using backend document data. */}
      <div className="stats-grid">
        <div className="stat-card">
          <span>Documents</span>
          <strong>{documents.length}</strong>
          <small>Uploaded files</small>
        </div>
        <div className="stat-card">
          <span>Indexed chunks</span>
          <strong>{totalChunks}</strong>
          <small>Searchable text sections</small>
        </div>
        <div className="stat-card">
          <span>Backend status</span>
          <strong className="status-value">{apiStatus}</strong>
          <small>FastAPI connection</small>
        </div>
      </div>

      {/* Provide shortcuts to the main document management features. */}
      <h2 className="section-heading">Quick actions</h2>
      <div className="action-grid">
        <Link to="/documents" className="action-card">
          <div className="action-icon">▤</div>
          <h3>Manage documents</h3>
          <p>Upload, view and remove your PDF, DOCX and other files.</p>
          <span>Open documents →</span>
        </Link>
        <Link to="/ask" className="action-card">
          <div className="action-icon">✧</div>
          <h3>Ask a question</h3>
          <p>Search your uploaded documents and view source citations.</p>
          <span>Start asking →</span>
        </Link>
      </div>

      {/* Display up to five recently returned documents. */}
      <h2 className="section-heading">Recent documents</h2>
      <div className="content-card">
        {documents.length === 0 ? (
          <p className="muted">No documents uploaded yet.</p>
        ) : (
          documents.slice(0, 5).map((doc) => (
            <div className="document-row" key={doc.document_id}>
              <span className="file-icon">PDF</span>
              <div className="document-row-info">
                <strong>{doc.filename}</strong>
                <small>{doc.chunk_count || 0} chunks</small>
              </div>
              <Link to="/documents" className="text-link">View</Link>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
