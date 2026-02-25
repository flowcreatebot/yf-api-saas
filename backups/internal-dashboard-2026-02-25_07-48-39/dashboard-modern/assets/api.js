function dashboardApiBase() {
  const path = window.location.pathname || "";
  if (path.startsWith("/dashboard")) return "/dashboard/api";
  return "/internal/api";
}

export async function getOverview(range) {
  const response = await fetch(`${dashboardApiBase()}/overview?range=${encodeURIComponent(range)}`);
  return handleJson(response);
}

export async function getMetrics(range) {
  const response = await fetch(`${dashboardApiBase()}/metrics?range=${encodeURIComponent(range)}`);
  return handleJson(response);
}

export async function getKeys() {
  const response = await fetch(`${dashboardApiBase()}/keys`);
  return handleJson(response);
}

export async function createKey(label, env) {
  const response = await fetch(`${dashboardApiBase()}/keys/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label, env }),
  });
  return handleJson(response);
}

export async function keyAction(id, action) {
  const response = await fetch(`${dashboardApiBase()}/keys/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
  });
  return handleJson(response);
}

export async function getActivity(filters = {}) {
  const params = new URLSearchParams();

  if (filters.status) params.set("status", filters.status);
  if (filters.action) params.set("action", filters.action);
  if (filters.limit != null && filters.limit !== "") params.set("limit", String(filters.limit));

  const query = params.toString();
  const response = await fetch(`${dashboardApiBase()}/activity${query ? `?${query}` : ""}`);
  return handleJson(response);
}

async function handleJson(response) {
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || payload?.message || "Request failed";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload;
}
