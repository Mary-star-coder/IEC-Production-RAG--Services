import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiRequest, saveSession } from "../lib/api";
import "./Auth.css";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSignup(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await apiRequest("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const tokenData = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password }),
      });
      if (!tokenData.access_token) throw new Error("Account bana, lekin login token nahi mila. Login page se sign in karein.");
      saveSession(tokenData.access_token, email.trim());
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
        <h1>Create your account</h1>
        <p className="auth-subtitle">Register securely to create your private document workspace.</p>
        <form onSubmit={handleSignup}>
          <label htmlFor="signup-email">Email address</label>
          <input id="signup-email" type="email" autoComplete="email" value={email}
            onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
          <label htmlFor="signup-password">Password</label>
          <input id="signup-password" type="password" autoComplete="new-password"
            value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters" minLength={8} maxLength={128} required />
          {error && <div className="notice error-notice">{error}</div>}
          <button className="auth-button" type="submit" disabled={loading}>
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
      </div>
    </div>
  );
}
