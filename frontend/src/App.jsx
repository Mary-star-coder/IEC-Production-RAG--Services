
import { Navigate, Route, Routes } from "react-router-dom";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import Ask from "./pages/Ask";
import DashboardLayout from "./layouts/DashboardLayout";

// Protect dashboard pages by checking whether a demo user is stored.
function ProtectedLayout() {
  const user = localStorage.getItem("ragflow_demo_user");

  // Redirect users to login if no demo user is available.
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Render the shared dashboard layout for authenticated demo users.
  return <DashboardLayout />;
}

// Define the application's routes and page navigation.
export default function App() {
  return (
    <Routes>
      {/* Redirect the home page to the login screen. */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Public routes available without login. */}
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      {/* Protect dashboard-related pages using the shared layout. */}
      <Route element={<ProtectedLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/ask" element={<Ask />} />
      </Route>

      {/* Redirect unknown URLs to the login page. */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
