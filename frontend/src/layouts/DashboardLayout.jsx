
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import "./DashboardLayout.css";

// Provide a shared layout for all dashboard pages.
export default function DashboardLayout() {
  // Initialize navigation to redirect the user after logout.
  const navigate = useNavigate();

  // Retrieve the demo user information stored during login.
  const user = JSON.parse(localStorage.getItem("ragflow_demo_user") || "{}");

  // Remove the demo session and redirect the user to the login page.
  function logout() {
    localStorage.removeItem("ragflow_demo_user");
    navigate("/login");
  }

  return (
    <div className="app-layout">
      {/* Sidebar contains application branding, navigation, and user information. */}
      <aside className="sidebar">
        {/* Display the application name in the sidebar. */}
        <div className="sidebar-brand">RAG<span>Flow</span></div>

        {/* Label for the main navigation section. */}
        <p className="sidebar-label">WORKSPACE</p>

        {/* Provide navigation links to the main dashboard pages. */}
        <nav className="sidebar-nav">
          <NavLink to="/dashboard">▦ <span>Dashboard</span></NavLink>
          <NavLink to="/documents">▤ <span>Documents</span></NavLink>
          <NavLink to="/ask">✧ <span>Ask Questions</span></NavLink>
        </nav>

        {/* Display the current demo user's profile and logout control. */}
        <div className="sidebar-bottom">
          {/* Show the first letter of the user's name as the avatar. */}
          <div className="user-avatar">
            {(user.name || "U").charAt(0).toUpperCase()}
          </div>

          {/* Display the user's name and email with fallback values. */}
          <div className="user-info">
            <strong>{user.name || "User"}</strong>
            <small>{user.email || "Demo account"}</small>
          </div>

          {/* Clear the demo session when the user clicks logout. */}
          <button onClick={logout} className="logout-button" title="Logout">
            ↪
          </button>
        </div>
      </aside>

      {/* Main area contains the shared header and active page content. */}
      <main className="main-area">
        <header className="topbar">
          {/* Display the workspace title and API status label. */}
          <span>Production RAG Workspace</span>
          <span className="online-label">● API workspace</span>
        </header>

        {/* Render the nested page selected through React Router. */}
        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
