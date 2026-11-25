import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiRequest, saveSession } from "../lib/api";
import "./Auth.css";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password }),
      });
      if (!data.access_token) throw new Error("Backend ne access token return nahi kiya.");
      saveSession(data.access_token, email.trim());
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">RAG<span>Flow</span></div>
        <div className="auth-icon">âœ¦</div>
        <h1>Welcome back</h1>
        <p className="auth-subtitle">Sign in to continue to your document workspace.</p>
        <form onSubmit={handleLogin}>
          <label htmlFor="login-email">Email address</label>
          <input id="login-email" type="email" autoComplete="email" value={email}
            onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
          <label htmlFor="login-password">Password</label>
          <input id="login-password" type="password" autoComplete="current-password"
            value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <div className="notice error-notice">{error}</div>}
          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="auth-switch">Don't have an account? <Link to="/signup">Create account</Link></p>
      </div>
    </div>
  );
}
