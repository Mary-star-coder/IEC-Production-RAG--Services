import { useEffect, useRef, useState } from "react";
import { apiRequest, uploadDocuments } from "../lib/api";
import "./Pages.css";

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const fileInput = useRef(null);

  async function loadDocuments() {
    setError("");
    try {
      const data = await apiRequest("/api/documents/");
      setDocuments(Array.isArray(data) ? data : data.documents || []);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { loadDocuments(); }, []);

  async function uploadFiles(e) {
    e.preventDefault();
    if (!files.length) { setError("Please select at least one file."); return; }
    setLoading(true);
    setError("");
    setMessage("");
    const results = await uploadDocuments(files);
    const uploaded = results
      .filter((result) => !result.error)
      .map((result) => result.file.name);
    const failed = results
      .filter((result) => result.error)
      .map((result) => `${result.file.name}: ${result.error.message}`);

    setFiles([]);
    if (fileInput.current) fileInput.current.value = "";
    if (uploaded.length) setMessage(`Uploaded successfully: ${uploaded.join(", ")}`);
    if (failed.length) setError(failed.join(" | "));
    await loadDocuments();
    setLoading(false);
  }

  async function deleteDocument(id, filename) {
    if (!window.confirm(`Delete ${filename}?`)) return;
    setError("");
    setMessage("");
    try {
      await apiRequest(`/api/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
      setMessage(`${filename} deleted successfully.`);
      await loadDocuments();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <p className="eyebrow">YOUR PRIVATE KNOWLEDGE BASE</p>
      <h1>Documents</h1>
      <p className="muted">Upload and manage the files your RAG system can search.</p>
      <form className="content-card upload-card" onSubmit={uploadFiles}>
        <div className="upload-symbol">↑</div>
        <h2>Upload your documents</h2>
        <p className="muted">Supported: PDF, DOCX, PPTX, TXT, MD Â· Maximum 15 MB per file</p>
        <input ref={fileInput} type="file" multiple accept=".pdf,.docx,.pptx,.txt,.md"
          onChange={(e) => setFiles(Array.from(e.target.files || []))} />
        {files.length > 0 && <p className="muted">{files.length} file(s) selected</p>}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "Uploading..." : "Upload selected files"}
        </button>
      </form>
      {message && <div className="notice success-notice">{message}</div>}
      {error && <div className="notice error-notice">{error}</div>}
      <div className="section-title-row">
        <div><h2 className="section-heading">Your files</h2><p className="muted">{documents.length} document(s) in your library</p></div>
        <button className="secondary-button" type="button" onClick={loadDocuments}>Refresh</button>
      </div>
      <div className="content-card">
        {documents.length === 0 ? <p className="muted">No documents found. Upload your first file above.</p> :
          documents.map((doc) => (
            <div className="document-row" key={doc.document_id}>
              <span className="file-icon">FILE</span>
              <div className="document-row-info">
                <strong>{doc.filename}</strong>
                <small>{doc.file_type || "Document"} Â· {doc.chunk_count || 0} chunks
                  {doc.file_size ? ` . ${(doc.file_size / 1024 / 1024).toFixed(2)} MB` : ""}
                </small>
              </div>
              <button className="delete-button" type="button"
                onClick={() => deleteDocument(doc.document_id, doc.filename)}>Delete</button>
            </div>
          ))}
      </div>
    </div>
  );
}
