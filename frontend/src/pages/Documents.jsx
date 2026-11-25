
import { useEffect, useRef, useState } from "react";
import "./Pages.css";

// Backend API base URL for document management operations.
const API = "";

// Render the document library with upload, listing, and deletion features.
export default function Documents() {
  // Store the documents currently available in the knowledge base.
  const [documents, setDocuments] = useState([]);

  // Store the files selected by the user for upload.
  const [files, setFiles] = useState([]);

  // Track upload progress and user-facing success or error messages.
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // Keep a reference to the file input so it can be reset after uploading.
  const fileInput = useRef(null);

  // Fetch the current document list from the backend.
  async function loadDocuments() {
    try {
      const res = await fetch(`${API}/api/documents/`);

      // Handle unsuccessful responses from the document listing endpoint.
      if (!res.ok) throw new Error("Could not load documents.");

      const data = await res.json();

      // Support both direct arrays and wrapped document responses.
      setDocuments(Array.isArray(data) ? data : data.documents || []);
    } catch (err) {
      // Display an error if the document list cannot be retrieved.
      setError(err.message);
    }
  }

  // Load the document library when the page first renders.
  useEffect(() => {
    loadDocuments();
  }, []);

  // Upload all selected files to the backend one at a time.
  async function uploadFiles(e) {
    e.preventDefault();

    // Prevent submission when no files have been selected.
    if (!files.length) {
      setError("Please select at least one file.");
      return;
    }

    // Initialize upload state and clear previous notifications.
    setLoading(true);
    setError("");
    setMessage("");
    const uploaded = [];

    // Process each selected file using a separate multipart request.
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        // Send the current file to the document upload endpoint.
        const res = await fetch(`${API}/api/documents/upload`, {
          method: "POST",
          body: formData,
        });

        const data = await res.json();

        // Convert backend upload errors into readable messages.
        if (!res.ok) throw new Error(data.detail || "Upload failed.");

        // Record the filename after a successful upload.
        uploaded.push(file.name);
      } catch (err) {
        // Keep track of individual file failures while continuing other uploads.
        setError((prev) => prev ? `${prev} | ${file.name}: ${err.message}` : `${file.name}: ${err.message}`);
      }
    }

    // Clear the selected files and reset the file input control.
    setFiles([]);
    if (fileInput.current) fileInput.current.value = "";

    // Display the names of files uploaded successfully.
    if (uploaded.length) {
      setMessage(`Uploaded successfully: ${uploaded.join(", ")}`);
    }

    // Refresh the document list after the upload process.
    await loadDocuments();

    // Stop the upload loading indicator.
    setLoading(false);
  }

  // Delete a document after obtaining confirmation from the user.
  async function deleteDocument(id, filename) {
    if (!window.confirm(`Delete ${filename}?`)) return;

    // Clear previous notifications before starting the deletion request.
    setError("");
    setMessage("");

    try {
      // Send a DELETE request for the selected document ID.
      const res = await fetch(`${API}/api/documents/${id}`, {
        method: "DELETE",
      });

      const data = await res.json();

      // Handle errors returned by the backend.
      if (!res.ok) throw new Error(data.detail || "Delete failed.");

      // Confirm successful deletion and refresh the document library.
      setMessage(`${filename} deleted successfully.`);
      await loadDocuments();
    } catch (err) {
      // Display the deletion error if the request fails.
      setError(err.message);
    }
  }

  return (
    <div className="page">
      {/* Introduce the document management section. */}
      <p className="eyebrow">YOUR KNOWLEDGE BASE</p>
      <h1>Documents</h1>
      <p className="muted">Upload and manage the files your RAG system can search.</p>

      {/* Provide a file selection and upload form. */}
      <form className="content-card upload-card" onSubmit={uploadFiles}>
        <div className="upload-symbol">↑</div>
        <h2>Upload your documents</h2>
        <p className="muted">Supported: PDF, DOCX, PPTX, TXT, MD · Maximum 15 MB per file</p>
        <input
          ref={fileInput}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,.txt,.md"
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
        />

        {/* Show how many files the user has selected. */}
        {files.length > 0 && (
          <p className="muted">{files.length} file(s) selected</p>
        )}

        {/* Disable the upload button while files are being processed. */}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "Uploading..." : "Upload selected files"}
        </button>
      </form>

      {/* Display upload success messages and any errors. */}
      {message && <div className="notice success-notice">{message}</div>}
      {error && <div className="notice error-notice">{error}</div>}

      {/* Provide a manual refresh option and show the document count. */}
      <div className="section-title-row">
        <div>
          <h2 className="section-heading">Your files</h2>
          <p className="muted">{documents.length} document(s) in your library</p>
        </div>
        <button className="secondary-button" onClick={loadDocuments}>Refresh</button>
      </div>

      {/* Render the document list or an empty-library message. */}
      <div className="content-card">
        {documents.length === 0 ? (
          <p className="muted">No documents found. Upload your first file above.</p>
        ) : (
          documents.map((doc) => (
            <div className="document-row" key={doc.document_id}>
              <span className="file-icon">FILE</span>
              <div className="document-row-info">
                <strong>{doc.filename}</strong>
                <small>
                  {doc.file_type || "Document"} · {doc.chunk_count || 0} chunks
                  {doc.file_size ? ` · ${(doc.file_size / 1024 / 1024).toFixed(2)} MB` : ""}
                </small>
              </div>

              {/* Allow the user to delete an individual document. */}
              <button
                className="delete-button"
                onClick={() => deleteDocument(doc.document_id, doc.filename)}
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
