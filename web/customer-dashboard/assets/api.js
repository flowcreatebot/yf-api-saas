const SESSION_STORAGE_KEY = "yfCustomerSession";

function dashboardApiBase() {
  return "/dashboard/api";
}

export function readStoredSession() {
  try {
    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    if (!parsed?.token || !parsed?.email || !parsed?.tenantId) {
      return null;
    }

    return parsed;
  } catch (_err) {
    return null;
  }
}

export function storeSession(session) {
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredSession() {
  window.localStorage.removeItem(SESSION_STORAGE_KEY);
}

function authHeaders() {
  const session = readStoredSession();
  if (!session?.token) {
    return {};
  }

  return {
    Authorization: `Bearer ${session.token}`,
  };
}

async function fetchJson(path, init = {}) {
  const headers = {
    ...(init.headers || {}),
    ...authHeaders(),
  };
  const response = await fetch(`${dashboardApiBase()}${path}`, {
    ...init,
    headers,
  });
  return handleJson(response);
}

export async function registerCustomerSession(email, password) {
  return fetchJson("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function loginCustomerSession(email, password) {
  return fetchJson("/session/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function logoutCustomerSession() {
  return fetchJson("/session/logout", { method: "POST" });
}

export async function getCustomerSession() {
  return fetchJson("/session/me");
}

export async function getOverview(range) {
  return fetchJson(`/overview?range=${encodeURIComponent(range)}`);
}

export async function getMetrics(range) {
  return fetchJson(`/metrics?range=${encodeURIComponent(range)}`);
}

export async function getKeys() {
  return fetchJson("/keys");
}

export async function createKey(label, env) {
  return fetchJson("/keys/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label, env }),
  });
}

export async function keyAction(id, action) {
  return fetchJson(`/keys/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
  });
}

export async function getActivity(filters = {}) {
  const params = new URLSearchParams();

  if (filters.status) params.set("status", filters.status);
  if (filters.action) params.set("action", filters.action);
  if (filters.limit != null && filters.limit !== "") params.set("limit", String(filters.limit));

  const query = params.toString();
  return fetchJson(`/activity${query ? `?${query}` : ""}`);
}

async function handleJson(response) {
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || payload?.message || "Request failed";
    const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
    error.status = response.status;
    throw error;
  }
  return payload;
}
