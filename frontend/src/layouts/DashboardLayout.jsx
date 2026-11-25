import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearSession, getUser } from "../lib/api";
import "./DashboardLayout.css";

export default function DashboardLayout() {
  const navigate = useNavigate();
  const user = getUser();

  function logout() {
    clearSession();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">RAG<span>Flow</span></div>
        <p className="sidebar-label">WORKSPACE</p>
        <nav className="sidebar-nav">
          <NavLink to="/dashboard">â–¦ <span>Dashboard</span></NavLink>
          <NavLink to="/documents">â–¤ <span>Documents</span></NavLink>
          <NavLink to="/ask">âœ§ <span>Ask Questions</span></NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="user-avatar">{(user?.email || "U").charAt(0).toUpperCase()}</div>
          <div className="user-info">
            <strong>Account</strong>
            <small>{user?.email || "Signed in"}</small>
          </div>
          <button onClick={logout} className="logout-button" title="Logout" aria-label="Logout">â†ª</button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <span>Production RAG Workspace</span>
          <span className="online-label">â— Authenticated session</span>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  );
}
