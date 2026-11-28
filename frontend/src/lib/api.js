const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
let refreshPromise;

export function getToken() {
  return localStorage.getItem("ragflow_access_token");
}

export function getRefreshToken() {
  return localStorage.getItem("ragflow_refresh_token");
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem("ragflow_user") || "null");
  } catch {
    return null;
  }
}

export function saveSession(token, email, refreshToken) {
  localStorage.setItem("ragflow_access_token", token);
  if (refreshToken) {
    localStorage.setItem("ragflow_refresh_token", refreshToken);
  } else {
    localStorage.removeItem("ragflow_refresh_token");
  }
  localStorage.setItem("ragflow_user", JSON.stringify({ email }));
  localStorage.removeItem("ragflow_demo_user");
}

export function clearSession() {
  localStorage.removeItem("ragflow_access_token");
  localStorage.removeItem("ragflow_refresh_token");
  localStorage.removeItem("ragflow_user");
  localStorage.removeItem("ragflow_demo_user");
}

async function sendRequest(path, options, token) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const isFormData = options.body instanceof FormData;
  if (options.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    return await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error("Could not reach the API. Check that the backend is running.");
  }
}

async function readResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json")
    ? await response.json()
    : await response.text();
}

function showLogin() {
  clearSession();
  if (window.location.pathname !== "/login") window.location.assign("/login");
}

function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const previousAccessToken = getToken();
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        showLogin();
        throw new Error("Session expired. Please sign in again.");
      }

      const response = await sendRequest(
        "/api/auth/refresh",
        {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        },
        null,
      );
      const data = await readResponse(response);
      if (response.ok && data.access_token && data.refresh_token) {
        saveSession(
          data.access_token,
          data.email || getUser()?.email || "",
          data.refresh_token,
        );
        return data.access_token;
      }

      if (response.status === 401) {
        const latestAccessToken = getToken();
        const latestRefreshToken = getRefreshToken();
        if (
          latestAccessToken
          && latestRefreshToken
          && (
            latestAccessToken !== previousAccessToken
            || latestRefreshToken !== refreshToken
          )
        ) {
          return latestAccessToken;
        }
        showLogin();
        throw new Error("Session expired. Please sign in again.");
      }

      const detail = typeof data === "object" && data !== null
        ? data.detail
        : data;
      throw new Error(detail || `Session refresh failed (${response.status}).`);
    })().finally(() => {
      refreshPromise = undefined;
    });
  }
  return refreshPromise;
}

export async function apiRequest(path, options = {}) {
  let token = getToken();
  let response = await sendRequest(path, options, token);

  const isAuthRequest = path.startsWith("/api/auth/");
  if (response.status === 401 && !isAuthRequest && getRefreshToken()) {
    const currentToken = getToken();
    if (token && currentToken && currentToken !== token) {
      token = currentToken;
    } else {
      token = await refreshAccessToken();
    }
    response = await sendRequest(path, options, token);
  }

  const data = await readResponse(response);
  if (response.status === 401 && !isAuthRequest) {
    showLogin();
    throw new Error("Session expired or invalid. Please sign in again.");
  }

  if (!response.ok) {
    const detail = typeof data === "object" && data !== null ? data.detail : data;
    throw new Error(detail || `Request failed (${response.status}).`);
  }

  return data;
}

export async function apiRequestWithToken(path, token, options = {}) {
  const response = await sendRequest(path, options, token);
  const data = await readResponse(response);
  if (!response.ok) {
    const detail = typeof data === "object" && data !== null ? data.detail : data;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}
