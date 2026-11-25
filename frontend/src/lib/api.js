const API_BASE = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

export function getToken() {
  return localStorage.getItem("ragflow_access_token");
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem("ragflow_user") || "null");
  } catch {
    return null;
  }
}

export function saveSession(token, email) {
  localStorage.setItem("ragflow_access_token", token);
  localStorage.setItem("ragflow_user", JSON.stringify({ email }));
  localStorage.removeItem("ragflow_demo_user");
}

export function clearSession() {
  localStorage.removeItem("ragflow_access_token");
  localStorage.removeItem("ragflow_user");
  localStorage.removeItem("ragflow_demo_user");
}

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();

  if (token) headers.set("Authorization", `Bearer ${token}`);

  const isFormData = options.body instanceof FormData;
  if (options.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error("Backend se connection nahi ho saka. API server aur VITE_API_URL check karein.");
  }

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (response.status === 401) {
    clearSession();
    if (window.location.pathname !== "/login") window.location.assign("/login");
    throw new Error("Session expire ya invalid hai. Dobara login karein.");
  }

  if (!response.ok) {
    const detail = typeof data === "object" && data !== null ? data.detail : data;
    throw new Error(detail || `Request failed (${response.status}).`);
  }

  return data;
}
