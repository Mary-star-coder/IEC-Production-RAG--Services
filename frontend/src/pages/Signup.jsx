
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Auth.css";

// Render the signup page and create a temporary demo user account.
export default function Signup() {
  // Store the name, email, and password entered by the user.
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Initialize navigation for redirecting after account creation.
  const navigate = useNavigate();

  // Handle submission of the signup form.
  function handleSignup(e) {
    e.preventDefault();

    // Temporary demo implementation: store basic user details in local storage.
    // This does not create a real backend account or securely store a password.
    localStorage.setItem("ragflow_demo_user", JSON.stringify({ name, email }));

    // Redirect the new demo user to the dashboard.
    navigate("/dashboard");
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Display application branding and the signup icon. */}
        <div className="auth-brand">RAG<span>Flow</span></div>
        <div className="auth-icon">✦</div>

        {/* Introduce the account creation form. */}
        <h1>Create your account</h1>
        <p className="auth-subtitle">
          Start asking questions from your documents.
        </p>

        {/* Collect the user's details and submit the signup form. */}
        <form onSubmit={handleSignup}>
          <label>Full name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            required
          />

          <label>Email address</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />

          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Create a password"
            minLength={8}
            required
          />

          <button className="auth-button" type="submit">
            Create account
          </button>
        </form>

        {/* Provide a link for existing users to return to the login page. */}
        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
