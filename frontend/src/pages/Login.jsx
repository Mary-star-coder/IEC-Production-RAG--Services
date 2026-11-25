
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Auth.css";

// Render the login page and handle demo account sign-in.
export default function Login() {
  // Store the email and password entered by the user.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Initialize navigation for redirecting after login.
  const navigate = useNavigate();

  // Validate the demo account and handle the login form submission.
  function handleLogin(e) {
    e.preventDefault();

    // Temporary frontend demo only. This does not perform real authentication.
    const user = localStorage.getItem("ragflow_demo_user");

    // Require the user to create a demo account before signing in.
    if (!user) {
      alert("Please create an account first.");
      return;
    }

    // Parse the saved demo user information from local storage.
    const savedUser = JSON.parse(user);

    // Check whether the entered email matches the saved demo account.
    if (savedUser.email !== email) {
      alert("No demo account found with this email. Please sign up.");
      return;
    }

    // Redirect the user to the dashboard after successful demo validation.
    navigate("/dashboard");
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Display application branding and the login icon. */}
        <div className="auth-brand">RAG<span>Flow</span></div>
        <div className="auth-icon">✦</div>

        {/* Introduce the login page to returning users. */}
        <h1>Welcome back</h1>
        <p className="auth-subtitle">
          Sign in to continue to your document workspace.
        </p>

        {/* Submit the login form using the handleLogin function. */}
        <form onSubmit={handleLogin}>
          <label>Email address</label>
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label>Password</label>
          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit" className="auth-button">
            Sign in
          </button>
        </form>

        {/* Provide a link for users who need to create an account. */}
        <p className="auth-switch">
          Don't have an account? <Link to="/signup">Create account</Link>
        </p>
      </div>
    </div>
  );
}
