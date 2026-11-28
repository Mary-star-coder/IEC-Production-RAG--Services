import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequestWithToken } from "../lib/api";
import "./Auth.css";

function readRecoveryToken() {
  const query = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.slice(1));
  return hash.get("access_token") || query.get("access_token");
}

export default function ResetPassword() {
  const [recoveryToken] = useState(readRecoveryToken);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(
    recoveryToken
      ? ""
      : "This reset link is invalid or expired. Request a new one.",
  );
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (window.location.hash || window.location.search) {
      window.history.replaceState(
        null,
        "",
        window.location.pathname,
      );
    }
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!recoveryToken) {
      setError("This reset link is invalid or expired. Request a new one.");
      return;
    }
    if (password !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const result = await apiRequestWithToken(
        "/api/auth/password",
        recoveryToken,
        {
          method: "PUT",
          body: JSON.stringify({ password }),
        },
      );
      setMessage(result.message);
      setPassword("");
      setConfirmPassword("");
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
        <div className="auth-icon">✓</div>
        <h1>Choose a new password</h1>
        <p className="auth-subtitle">
          Use at least 8 characters for your new password.
        </p>
        {!message ? (
          <form onSubmit={handleSubmit}>
            <label htmlFor="new-password">New password</label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            <label htmlFor="confirm-password">Confirm new password</label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
            {error && <div className="notice error-notice">{error}</div>}
            <button
              type="submit"
              className="auth-button"
              disabled={loading || !recoveryToken}
            >
              {loading ? "Updating..." : "Update password"}
            </button>
          </form>
        ) : (
          <div className="notice success-notice">{message}</div>
        )}
        {error && message && <div className="notice error-notice">{error}</div>}
        <p className="auth-switch">
          <Link to="/login">{message ? "Continue to sign in" : "Back to sign in"}</Link>
        </p>
      </div>
    </div>
  );
}
