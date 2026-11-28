import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { getToken } from "./lib/api";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import ChatWorkspace from "./pages/ChatWorkspace";

function ProtectedLayout() {
  return getToken() ? <Outlet /> : <Navigate to="/login" replace />;
}

function PublicOnly({ children }) {
  return getToken() ? <Navigate to="/dashboard" replace /> : children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/signup" element={<PublicOnly><Signup /></PublicOnly>} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/dashboard" element={<ChatWorkspace />} />
        <Route path="/documents" element={<Navigate to="/dashboard" replace />} />
        <Route path="/ask" element={<Navigate to="/dashboard" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
