import { useEffect, useRef, useState } from "react";
import {
  FileText,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquare,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import {
  apiRequest,
  clearSession,
  getUser,
  uploadDocuments,
} from "../lib/api";
import "./ChatWorkspace.css";

function getList(data, key) {
  if (Array.isArray(data)) return data;
  return Array.isArray(data?.[key]) ? data[key] : [];
}

function formatBytes(bytes) {
  if (!bytes) return "Document";
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function ChatWorkspace() {
  const [documents, setDocuments] = useState([]);
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [turns, setTurns] = useState([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState(null);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [loadingChat, setLoadingChat] = useState(false);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const fileInput = useRef(null);
  const messageEnd = useRef(null);
  const user = getUser();

  async function refreshDocuments() {
    const data = await apiRequest("/api/documents/");
    const nextDocuments = getList(data, "documents");
    setDocuments(nextDocuments);
    setSelectedDocumentIds((current) => {
      if (current === null) return null;
      const availableIds = new Set(
        nextDocuments.map((document) => document.document_id),
      );
      const selected = current.filter((id) => availableIds.has(id));
      return selected.length === nextDocuments.length ? null : selected;
    });
  }

  async function refreshChats() {
    const data = await apiRequest("/api/chats/");
    setChats(getList(data, "chats"));
  }

  useEffect(() => {
    let active = true;
    async function loadWorkspace() {
      try {
        const [documentResult, chatResult] = await Promise.allSettled([
          apiRequest("/api/documents/"),
          apiRequest("/api/chats/"),
        ]);
        if (!active) return;
        const loadErrors = [];
        if (documentResult.status === "fulfilled") {
          setDocuments(getList(documentResult.value, "documents"));
        } else {
          loadErrors.push(`Documents: ${documentResult.reason.message}`);
        }
        if (chatResult.status === "fulfilled") {
          setChats(getList(chatResult.value, "chats"));
        } else {
          loadErrors.push(`Chat history: ${chatResult.reason.message}`);
        }
        if (loadErrors.length) setError(loadErrors.join(" "));
      } finally {
        if (active) setLoadingWorkspace(false);
      }
    }
    loadWorkspace();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    messageEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, sending]);

  function startNewChat() {
    setActiveChatId(null);
    setTurns([]);
    setQuestion("");
    setError("");
    setNotice("");
    setSelectedDocumentIds(null);
    setSidebarOpen(false);
  }

  async function openChat(chat) {
    if (chat.id === activeChatId) {
      setSidebarOpen(false);
      return;
    }
    setLoadingChat(true);
    setActiveChatId(chat.id);
    setTurns([]);
    setError("");
    setNotice("");
    setSidebarOpen(false);
    try {
      const data = await apiRequest(`/api/chats/${encodeURIComponent(chat.id)}`);
      const nextTurns = getList(data, "turns");
      setTurns(nextTurns);
      const selection = nextTurns.at(-1)?.selected_document_ids;
      setSelectedDocumentIds(Array.isArray(selection) ? selection : null);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoadingChat(false);
    }
  }

  async function removeChat(chat) {
    if (!window.confirm(`Delete chat "${chat.title}" and its history?`)) return;
    setError("");
    try {
      await apiRequest(`/api/chats/${encodeURIComponent(chat.id)}`, {
        method: "DELETE",
      });
      setChats((current) => current.filter((item) => item.id !== chat.id));
      if (activeChatId === chat.id) startNewChat();
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  function toggleDocument(documentId) {
    const allIds = documents.map((document) => document.document_id);
    const currentIds = new Set(selectedDocumentIds ?? allIds);
    if (currentIds.has(documentId)) currentIds.delete(documentId);
    else currentIds.add(documentId);
    setSelectedDocumentIds(
      currentIds.size === allIds.length
        ? null
        : allIds.filter((id) => currentIds.has(id)),
    );
  }

  function toggleAllDocuments() {
    setSelectedDocumentIds((current) => (
      current === null ? [] : null
    ));
  }

  async function uploadFiles(event) {
    event.preventDefault();
    const files = Array.from(fileInput.current?.files ?? []);
    if (!files.length) {
      setError("Choose at least one document to upload.");
      return;
    }
    setUploading(true);
    setError("");
    setNotice("");
    const results = await uploadDocuments(files);
    const uploaded = results
      .filter((result) => !result.error)
      .map((result) => result.file.name);
    const failed = results
      .filter((result) => result.error)
      .map((result) => `${result.file.name}: ${result.error.message}`);
    if (fileInput.current) fileInput.current.value = "";
    try {
      await refreshDocuments();
      if (uploaded.length) {
        setNotice(
          `${uploaded.length} document${uploaded.length === 1 ? "" : "s"} added to your library.`,
        );
      }
    } catch (refreshError) {
      failed.push(`Library refresh failed: ${refreshError.message}`);
    }
    if (failed.length) setError(failed.join(" "));
    setUploading(false);
  }

  async function removeDocument(document) {
    if (!window.confirm(`Delete "${document.filename}" from your library?`)) {
      return;
    }
    setError("");
    setNotice("");
    try {
      await apiRequest(
        `/api/documents/${encodeURIComponent(document.document_id)}`,
        { method: "DELETE" },
      );
      await refreshDocuments();
      setNotice(`${document.filename} was deleted.`);
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  async function sendQuestion(event) {
    event.preventDefault();
    const text = question.trim();
    if (text.length < 3 || sending || loadingChat) return;
    if (documents.length && selectedDocumentIds?.length === 0) {
      setError("Select at least one document to search.");
      return;
    }
    if (!documents.length) {
      setError("Upload a document before asking a question.");
      return;
    }

    setSending(true);
    setError("");
    setNotice("");
    const pendingId = `pending-${Date.now()}`;
    setTurns((current) => [
      ...current,
      {
        id: pendingId,
        question: text,
        answer: "",
        citations: [],
        retrieved_chunks: [],
        selected_document_ids: selectedDocumentIds,
        pending: true,
      },
    ]);
    setQuestion("");

    try {
      let chatId = activeChatId;
      if (!chatId) {
        const created = await apiRequest("/api/chats/", {
          method: "POST",
          body: JSON.stringify({ title: text.slice(0, 80) }),
        });
        chatId = created.chat.id;
        setActiveChatId(chatId);
        setChats((current) => [created.chat, ...current]);
      }
      const result = await apiRequest("/api/questions/ask", {
        method: "POST",
        body: JSON.stringify({
          question: text,
          top_k: 5,
          chat_id: chatId,
          document_ids: selectedDocumentIds,
        }),
      });
      setTurns((current) => current.map((turn) => (
        turn.id === pendingId
          ? {
            ...result,
            id: `turn-${pendingId}`,
            question: text,
            selected_document_ids: selectedDocumentIds,
          }
          : turn
      )));
      try {
        await refreshChats();
      } catch (refreshError) {
        setError(`Answer saved, but chat history did not refresh: ${refreshError.message}`);
      }
    } catch (sendError) {
      setTurns((current) => current.map((turn) => (
        turn.id === pendingId
          ? { ...turn, pending: false, error: sendError.message }
          : turn
      )));
      setError(sendError.message);
    } finally {
      setSending(false);
    }
  }

  function logout() {
    clearSession();
    window.location.assign("/login");
  }

  const selectedCount = selectedDocumentIds === null
    ? documents.length
    : selectedDocumentIds.length;
  const activeChat = chats.find((chat) => chat.id === activeChatId);

  return (
    <div className="rag-workspace">
      {sidebarOpen && (
        <button
          className="rag-sidebar-backdrop"
          type="button"
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside className={`rag-sidebar${sidebarOpen ? " is-open" : ""}`}>
        <div className="rag-brand">
          <div className="rag-brand-mark"><Sparkles size={17} /></div>
          <span>RAGFlow</span>
          <button
            className="rag-icon-button rag-mobile-close"
            type="button"
            aria-label="Close sidebar"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <button className="rag-new-chat" type="button" onClick={startNewChat}>
          <Plus size={17} />
          <span>New chat</span>
        </button>

        <section className="rag-side-section rag-history-section">
          <div className="rag-section-heading">
            <span>Recent chats</span>
            <MessageSquare size={15} />
          </div>
          <div className="rag-chat-list">
            {chats.length === 0 ? (
              <p className="rag-side-empty">Your conversations will appear here.</p>
            ) : chats.map((chat) => (
              <div
                className={`rag-chat-entry${activeChatId === chat.id ? " is-active" : ""}`}
                key={chat.id}
              >
                <button
                  type="button"
                  className="rag-chat-open"
                  onClick={() => openChat(chat)}
                  title={chat.title}
                >
                  <MessageSquare size={15} />
                  <span>{chat.title || "New chat"}</span>
                </button>
                <button
                  className="rag-icon-button rag-chat-delete"
                  type="button"
                  aria-label={`Delete ${chat.title || "chat"}`}
                  title="Delete chat"
                  onClick={() => removeChat(chat)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="rag-side-section rag-library">
          <div className="rag-section-heading">
            <span>Document library</span>
            <span className="rag-doc-count">{documents.length}</span>
          </div>
          <button
            className="rag-upload-button"
            type="button"
            onClick={() => fileInput.current?.click()}
            disabled={uploading}
          >
            {uploading ? <LoaderCircle size={16} className="rag-spin" /> : <Upload size={16} />}
            <span>{uploading ? "Uploading..." : "Add documents"}</span>
            {!uploading && <Paperclip size={14} />}
          </button>
          <input
            ref={fileInput}
            className="rag-hidden-file-input"
            type="file"
            multiple
            accept=".pdf,.docx,.pptx,.txt,.md"
            onChange={uploadFiles}
            aria-label="Upload documents"
          />
          <div className="rag-source-summary">
            <span>Search sources</span>
            <span>{selectedCount} selected</span>
          </div>
          <label className="rag-document-option rag-all-documents">
            <input
              type="checkbox"
              checked={selectedDocumentIds === null}
              onChange={toggleAllDocuments}
              disabled={!documents.length}
            />
            <span className="rag-document-name">All documents</span>
          </label>
          <div className="rag-document-list">
            {loadingWorkspace && <p className="rag-side-empty">Loading library...</p>}
            {!loadingWorkspace && documents.length === 0 && (
              <p className="rag-side-empty">Upload files to start building your library.</p>
            )}
            {documents.map((document) => {
              const checked = selectedDocumentIds === null
                || selectedDocumentIds.includes(document.document_id);
              return (
                <div className="rag-document-row" key={document.document_id}>
                  <label className="rag-document-option">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleDocument(document.document_id)}
                    />
                    <FileText size={15} />
                    <span
                      className="rag-document-name"
                      title={document.filename}
                    >
                      {document.filename}
                    </span>
                    <span className="rag-document-meta">
                      {formatBytes(document.file_size)} · {document.chunk_count || 0} chunks
                    </span>
                  </label>
                  <button
                    className="rag-icon-button rag-document-delete"
                    type="button"
                    aria-label={`Delete ${document.filename}`}
                    title={`Delete ${document.filename}`}
                    onClick={() => removeDocument(document)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        <div className="rag-account">
          <div className="rag-avatar">
            {(user?.email || "U").charAt(0).toUpperCase()}
          </div>
          <div className="rag-account-copy">
            <strong>Workspace</strong>
            <span title={user?.email}>{user?.email || "Signed in"}</span>
          </div>
          <button
            className="rag-icon-button rag-logout"
            type="button"
            title="Sign out"
            aria-label="Sign out"
            onClick={logout}
          >
            <LogOut size={15} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="rag-main">
        <header className="rag-topbar">
          <button
            className="rag-icon-button rag-mobile-menu"
            type="button"
            aria-label="Open sidebar"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={19} />
          </button>
          <div className="rag-topbar-title">
            <strong>{activeChat?.title || "Document assistant"}</strong>
            <span>
              {selectedCount === documents.length
                ? "Searching your full library"
                : `Searching ${selectedCount} selected document${selectedCount === 1 ? "" : "s"}`}
            </span>
          </div>
          <button className="rag-topbar-new" type="button" onClick={startNewChat}>
            <Plus size={16} />
            <span>New chat</span>
          </button>
        </header>

        <div className="rag-chat-scroll">
          {error && <div className="rag-alert rag-alert-error" role="alert">{error}</div>}
          {notice && <div className="rag-alert rag-alert-success" role="status">{notice}</div>}

          {loadingChat ? (
            <div className="rag-loading-history">
              <LoaderCircle size={20} className="rag-spin" />
              <span>Loading conversation...</span>
            </div>
          ) : turns.length === 0 ? (
            <div className="rag-empty-chat">
              <div className="rag-empty-icon"><Sparkles size={24} /></div>
              <h1>What would you like to know?</h1>
              <p>Ask a question and get a grounded answer from your selected documents.</p>
              <div className="rag-suggestions">
                <button
                  type="button"
                  onClick={() => setQuestion("Summarize the key ideas in my documents.")}
                  disabled={!documents.length}
                >
                  <strong>Summarize key ideas</strong>
                  <span>Get a concise overview of your sources</span>
                </button>
                <button
                  type="button"
                  onClick={() => setQuestion("What are the most important facts?")}
                  disabled={!documents.length}
                >
                  <strong>Find important facts</strong>
                  <span>Search for details across selected files</span>
                </button>
              </div>
              {!documents.length && (
                <p className="rag-empty-hint">Add a document from the left panel to begin.</p>
              )}
            </div>
          ) : (
            <div className="rag-turn-list">
              {turns.map((turn, index) => (
                <article className="rag-turn" key={turn.id || index}>
                  <div className="rag-user-message">
                    <div className="rag-user-avatar">
                      {(user?.email || "U").charAt(0).toUpperCase()}
                    </div>
                    <p>{turn.question}</p>
                  </div>
                  {turn.pending ? (
                    <div className="rag-assistant-message rag-assistant-pending">
                      <span className="rag-assistant-mark"><Sparkles size={16} /></span>
                      <span><LoaderCircle size={16} className="rag-spin" /> Searching your sources...</span>
                    </div>
                  ) : turn.error ? (
                    <div className="rag-assistant-message rag-turn-error">
                      <span className="rag-assistant-mark"><Sparkles size={16} /></span>
                      <p>{turn.error}</p>
                    </div>
                  ) : (
                    <div className="rag-assistant-message">
                      <span className="rag-assistant-mark"><Sparkles size={16} /></span>
                      <div className="rag-answer-content">
                        <div className="rag-answer-text">
                          <ReactMarkdown>{turn.answer}</ReactMarkdown>
                        </div>
                        {turn.citations?.length > 0 && (
                          <details className="rag-citations">
                            <summary>
                              Sources used ({turn.citations.length})
                            </summary>
                            <div className="rag-citation-list">
                              {turn.citations.map((citation, citationIndex) => (
                                <div
                                  className="rag-citation"
                                  key={`${citation.filename}-${citation.page}-${citationIndex}`}
                                >
                                  <FileText size={15} />
                                  <span>{citation.filename}</span>
                                  <small>Page {citation.page}</small>
                                  <small>{Number(citation.similarity || 0).toFixed(2)} match</small>
                                </div>
                              ))}
                            </div>
                          </details>
                        )}
                        {turn.retrieved_chunks?.length > 0 && (
                          <details className="rag-evidence">
                            <summary>Show retrieved passages</summary>
                            <div className="rag-evidence-list">
                              {turn.retrieved_chunks.map((chunk, chunkIndex) => (
                                <blockquote key={`${chunk.metadata?.document_id}-${chunkIndex}`}>
                                  <span>
                                    {chunk.metadata?.filename || "Source"} · page {chunk.metadata?.page || "—"}
                                  </span>
                                  <p>{chunk.text}</p>
                                </blockquote>
                              ))}
                            </div>
                          </details>
                        )}
                        {turn.abstained && (
                          <span className="rag-abstained">No supporting passage found in this search.</span>
                        )}
                      </div>
                    </div>
                  )}
                </article>
              ))}
              <div ref={messageEnd} />
            </div>
          )}
        </div>

        <div className="rag-composer-wrap">
          <form className="rag-composer" onSubmit={sendQuestion}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder={
                documents.length
                  ? "Ask a question about your documents..."
                  : "Upload a document to start asking questions..."
              }
              rows={1}
              maxLength={1000}
              aria-label="Ask a question about your documents"
              disabled={!documents.length || sending || loadingChat}
            />
            <button
              className="rag-send-button"
              type="submit"
              aria-label="Send question"
              disabled={
                !documents.length
                || selectedCount === 0
                || question.trim().length < 3
                || sending
                || loadingChat
              }
            >
              {sending ? <LoaderCircle size={17} className="rag-spin" /> : <Send size={17} />}
            </button>
          </form>
          <p className="rag-composer-note">
            Answers use only the selected files. Verify important details against the cited passages.
          </p>
        </div>
      </main>
    </div>
  );
}
