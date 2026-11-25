import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiRequest } from "../lib/api";
import "./Pages.css";

export default function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [apiStatus, setApiStatus] = useState("Checking...");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiRequest("/api/documents/")
      .then((data) => {
        if (!active) return;
        setDocuments(Array.isArray(data) ? data : data.documents || []);
        setApiStatus("Connected");
      })
      .catch((err) => {
        if (!active) return;
        setApiStatus("Not connected");
        setError(err.message);
      });
    return () => { active = false; };
  }, []);

  const totalChunks = documents.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0);

  return (
    <div className="page">
      <div className="welcome-row">
        <div>
          <p className="eyebrow">OVERVIEW</p>
          <h1>Welcome to your workspace âœ¨</h1>
          <p className="muted">Manage documents and get answers from your private knowledge base.</p>
        </div>
        <Link className="primary-link" to="/documents">+ Upload document</Link>
      </div>
      {error && <div className="notice error-notice">{error}</div>}
      <div className="stats-grid">
        <div className="stat-card"><span>Documents</span><strong>{documents.length}</strong><small>Your uploaded files</small></div>
        <div className="stat-card"><span>Indexed chunks</span><strong>{totalChunks}</strong><small>Searchable text sections</small></div>
        <div className="stat-card"><span>Backend status</span><strong className="status-value">{apiStatus}</strong><small>Authenticated FastAPI connection</small></div>
      </div>
      <h2 className="section-heading">Quick actions</h2>
      <div className="action-grid">
        <Link to="/documents" className="action-card">
          <div className="action-icon">â–¤</div><h3>Manage documents</h3>
          <p>Upload, view and remove your PDF, DOCX and other files.</p><span>Open documents â†’</span>
        </Link>
        <Link to="/ask" className="action-card">
          <div className="action-icon">âœ§</div><h3>Ask a question</h3>
          <p>Search your documents and inspect supporting source citations.</p><span>Start asking â†’</span>
        </Link>
      </div>
      <h2 className="section-heading">Recent documents</h2>
      <div className="content-card">
        {documents.length === 0 ? <p className="muted">No documents uploaded yet.</p> :
          documents.slice(0, 5).map((doc) => (
            <div className="document-row" key={doc.document_id}>
              <span className="file-icon">FILE</span>
              <div className="document-row-info"><strong>{doc.filename}</strong><small>{doc.chunk_count || 0} chunks</small></div>
              <Link to="/documents" className="text-link">View</Link>
            </div>
          ))}
      </div>
    </div>
  );
}
