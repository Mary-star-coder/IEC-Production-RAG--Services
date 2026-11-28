import { useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../lib/api";
import "./Auth.css";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const result = await apiRequest("/api/auth/password-reset", {
        method: "POST",
        body: JSON.stringify({ email: email.trim() }),
      });
      setMessage(result.message);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">RAG<span>Flow</span></div>
        <div className="auth-icon">?</div>
        <h1>Reset your password</h1>
        <p className="auth-subtitle">
          Enter your account email and we’ll send a secure reset link.
        </p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="reset-email">Email address</label>
          <input
            id="reset-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
          />
          {error && <div className="notice error-notice">{error}</div>}
          {message && <div className="notice success-notice">{message}</div>}
          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? "Sending..." : "Send reset link"}
          </button>
        </form>
        <p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
      </div>
    </div>
  );
}
