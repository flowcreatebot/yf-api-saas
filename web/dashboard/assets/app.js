const SESSION_KEY = "yf_dashboard_session";
const USER_KEY = "yf_dashboard_user";
const KEYS_STATE_KEY = "yf_dashboard_keys_state";

const defaultKeys = [
  {
    id: "key_live_primary",
    label: "Primary production",
    prefix: "yf_live_••••",
    env: "live",
    active: true,
    lastUsed: "—",
  },
  {
    id: "key_test_zapier",
    label: "Zapier trial",
    prefix: "yf_test_••••",
    env: "test",
    active: true,
    lastUsed: "—",
  },
];

function isAuthed() {
  return localStorage.getItem(SESSION_KEY) === "1";
}

function ensureAuth() {
  if (!isAuthed()) {
    window.location.href = "./login.html";
  }
}

function loginPlaceholder(email) {
  localStorage.setItem(SESSION_KEY, "1");
  localStorage.setItem(USER_KEY, email || "owner@example.com");
}

function logoutPlaceholder() {
  localStorage.removeItem(SESSION_KEY);
  window.location.href = "./login.html";
}

function loadKeyState() {
  try {
    const raw = localStorage.getItem(KEYS_STATE_KEY);
    if (!raw) return [...defaultKeys];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [...defaultKeys];
    return parsed;
  } catch {
    return [...defaultKeys];
  }
}

function saveKeyState(keys) {
  localStorage.setItem(KEYS_STATE_KEY, JSON.stringify(keys));
}

function setKeysFeedback(text, level = "info") {
  const feedbackEl = document.getElementById("keys-feedback");
  if (!feedbackEl) return;
  feedbackEl.textContent = text;
  feedbackEl.style.color = level === "error" ? "var(--danger)" : "var(--muted)";
}

function setKeysBusy(isBusy) {
  document.querySelectorAll("#create-key-button, #keys-table-body .btn").forEach((el) => {
    el.disabled = isBusy;
  });
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload?.detail || payload?.error;
    const message = detail?.message || payload?.message || `request failed (${response.status})`;
    throw new Error(message);
  }

  return payload;
}

async function hydrateKeysFromApi() {
  try {
    const payload = await apiRequest("/internal/api/keys");
    if (Array.isArray(payload?.keys)) {
      saveKeyState(payload.keys);
      return payload.keys;
    }
    throw new Error("keys payload malformed");
  } catch {
    saveKeyState(defaultKeys);
    return [...defaultKeys];
  }
}

function badge(status) {
  if (status) return '<span class="badge ok">Active</span>';
  return '<span class="badge warn">Revoked</span>';
}

function renderKeys() {
  const tbody = document.getElementById("keys-table-body");
  if (!tbody) return;

  const keys = loadKeyState();
  tbody.innerHTML = "";

  keys.forEach((key) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${key.label}</td>
      <td>${key.prefix}</td>
      <td>${badge(key.active)}</td>
      <td>${key.lastUsed || "—"}</td>
      <td>
        <button class="btn btn-sm" onclick="dashboardApp.rotateKey('${key.id}')">Rotate</button>
        <button class="btn btn-sm" onclick="dashboardApp.toggleKeyStatus('${key.id}', ${Boolean(key.active)})">${key.active ? "Revoke" : "Activate"}</button>
      </td>
    `;
    tbody.appendChild(row);
  });
}

async function refreshKeys() {
  const keys = await hydrateKeysFromApi();
  renderKeys();
  return keys;
}

async function createKey(label, env) {
  setKeysBusy(true);
  try {
    await apiRequest("/internal/api/keys/create", {
      method: "POST",
      body: { label, env },
    });
    await refreshKeys();
    setKeysFeedback(`Created ${env} key '${label}' via mock-store API.`);
  } catch (error) {
    setKeysFeedback(`Failed to create key: ${error.message}`, "error");
  } finally {
    setKeysBusy(false);
  }
}

async function rotateKey(id) {
  setKeysBusy(true);
  try {
    await apiRequest(`/internal/api/keys/${encodeURIComponent(id)}/rotate`, { method: "POST" });
    await refreshKeys();
    setKeysFeedback(`Rotated key '${id}'. Masked prefix refreshed.`);
  } catch (error) {
    setKeysFeedback(`Failed to rotate key: ${error.message}`, "error");
  } finally {
    setKeysBusy(false);
  }
}

async function toggleKeyStatus(id, isActive) {
  setKeysBusy(true);
  const action = isActive ? "revoke" : "activate";
  try {
    await apiRequest(`/internal/api/keys/${encodeURIComponent(id)}/${action}`, { method: "POST" });
    await refreshKeys();
    setKeysFeedback(`${isActive ? "Revoked" : "Activated"} key '${id}'.`);
  } catch (error) {
    setKeysFeedback(`Failed to ${action} key: ${error.message}`, "error");
  } finally {
    setKeysBusy(false);
  }
}

function attachHandlers() {
  const form = document.getElementById("create-key-form");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const labelInput = document.getElementById("key-label");
    const envInput = document.getElementById("key-env");

    const label = labelInput?.value?.trim();
    const env = envInput?.value || "test";

    if (!label) {
      setKeysFeedback("Label is required.", "error");
      return;
    }

    await createKey(label, env);
    form.reset();
  });
}

function setActiveNav(page) {
  document.querySelectorAll("[data-nav]").forEach((item) => {
    item.classList.toggle("active", item.dataset.nav === page);
  });
}

function initUserText() {
  const userEl = document.getElementById("current-user");
  if (userEl) {
    userEl.textContent = localStorage.getItem(USER_KEY) || "owner@example.com";
  }
}

async function loadOverviewPayload() {
  const response = await fetch("/internal/api/overview", { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`overview request failed (${response.status})`);
  }
  return response.json();
}

function renderOverview(payload) {
  const requestsEl = document.getElementById("kpi-requests-24h");
  const errorRateEl = document.getElementById("kpi-error-rate");
  const calloutEl = document.getElementById("overview-callout");

  if (requestsEl) requestsEl.textContent = Number(payload.requests24h || 0).toLocaleString();
  if (errorRateEl) errorRateEl.textContent = `${Number(payload.errorRatePct || 0).toFixed(2)}%`;
  if (calloutEl) {
    calloutEl.textContent =
      "Loaded from /internal/api/overview placeholder payload. Swap in real analytics source next milestone.";
  }
}

function renderMetrics(payload) {
  const p95El = document.getElementById("kpi-p95");
  const fiveXxEl = document.getElementById("kpi-5xx");
  const tableBody = document.getElementById("metrics-table-body");
  const calloutEl = document.getElementById("metrics-callout");

  if (p95El) p95El.textContent = `${Number(payload.p95LatencyMs || 0)} ms`;
  if (fiveXxEl) fiveXxEl.textContent = Number(payload.fiveXx24h || 0).toLocaleString();

  if (tableBody && Array.isArray(payload.topEndpoints)) {
    tableBody.innerHTML = "";
    payload.topEndpoints.forEach((endpoint) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${endpoint.path}</td>
        <td>${Number(endpoint.requests || 0).toLocaleString()}</td>
        <td>${Number(endpoint.errorPct || 0).toFixed(2)}%</td>
        <td>${Number(endpoint.p95Ms || 0)} ms</td>
      `;
      tableBody.appendChild(row);
    });
  }

  if (calloutEl) {
    calloutEl.textContent =
      "Metrics shown from placeholder internal API. Add per-tenant filtering and real charts after auth wiring.";
  }
}

function renderMetricsError(error) {
  const calloutEl = document.getElementById("metrics-callout");
  const tableBody = document.getElementById("metrics-table-body");

  if (tableBody) {
    tableBody.innerHTML = `<tr><td colspan="4" class="small">Failed to load metrics: ${error.message}</td></tr>`;
  }

  if (calloutEl) {
    calloutEl.textContent = "Could not load placeholder metrics payload.";
  }
}

async function bootstrap(page) {
  ensureAuth();
  setActiveNav(page);
  initUserText();

  if (page === "keys") {
    try {
      await refreshKeys();
      setKeysFeedback("Mock-store API connected. Use actions to simulate lifecycle events.");
    } catch {
      renderKeys();
      setKeysFeedback("Using local fallback state (internal API unavailable).", "error");
    }
    attachHandlers();
  }

  if (page === "overview" || page === "metrics") {
    try {
      const payload = await loadOverviewPayload();
      if (page === "overview") renderOverview(payload);
      if (page === "metrics") renderMetrics(payload);
    } catch (error) {
      if (page === "metrics") {
        renderMetricsError(error);
      }
      if (page === "overview") {
        const calloutEl = document.getElementById("overview-callout");
        if (calloutEl) calloutEl.textContent = "Could not load placeholder summary.";
      }
    }
  }
}

window.dashboardApp = {
  ensureAuth,
  bootstrap,
  loginPlaceholder,
  logoutPlaceholder,
  rotateKey,
  toggleKeyStatus,
};
