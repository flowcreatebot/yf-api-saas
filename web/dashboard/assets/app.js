const SESSION_KEY = "yf_dashboard_session";
const USER_KEY = "yf_dashboard_user";
const KEYS_STATE_KEY = "yf_dashboard_keys_state";
const METRICS_RANGE_KEY = "yf_dashboard_metrics_range";

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

function getMetricsRange() {
  const selected = localStorage.getItem(METRICS_RANGE_KEY);
  if (selected === "7d" || selected === "30d") return selected;
  return "24h";
}

function setMetricsRange(range) {
  const selected = range === "7d" || range === "30d" ? range : "24h";
  localStorage.setItem(METRICS_RANGE_KEY, selected);
  return selected;
}

function rangeLabel(range) {
  if (range === "7d") return "7d";
  if (range === "30d") return "30d";
  return "24h";
}

function setActiveMetricsRange(range) {
  document.querySelectorAll("[data-range]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.range === range);
  });
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

async function loadOverviewPayload(range = "24h") {
  const selected = range === "7d" || range === "30d" ? range : "24h";
  const response = await fetch(`/internal/api/overview?range=${encodeURIComponent(selected)}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`overview request failed (${response.status})`);
  }
  return response.json();
}

function renderOverview(payload) {
  const requestsEl = document.getElementById("kpi-requests-24h");
  const errorRateEl = document.getElementById("kpi-error-rate");
  const calloutEl = document.getElementById("overview-callout");

  if (requestsEl) requestsEl.textContent = Number(payload.requests24h || payload.requests || 0).toLocaleString();
  if (errorRateEl) errorRateEl.textContent = `${Number(payload.errorRatePct || 0).toFixed(2)}%`;
  if (calloutEl) {
    calloutEl.textContent =
      "Loaded from /internal/api/overview placeholder payload. Swap in real analytics source next milestone.";
  }
}

function renderMetrics(payload) {
  const selectedRange = payload?.range || getMetricsRange();
  const p95El = document.getElementById("kpi-p95");
  const fiveXxEl = document.getElementById("kpi-5xx");
  const fiveXxLabelEl = document.getElementById("kpi-5xx-label");
  const requestsColLabelEl = document.getElementById("requests-col-label");
  const tableBody = document.getElementById("metrics-table-body");
  const calloutEl = document.getElementById("metrics-callout");

  if (p95El) p95El.textContent = `${Number(payload.p95LatencyMs || 0)} ms`;
  if (fiveXxEl) fiveXxEl.textContent = Number(payload.fiveXx ?? payload.fiveXx24h ?? 0).toLocaleString();
  if (fiveXxLabelEl) fiveXxLabelEl.textContent = `5xx (${rangeLabel(selectedRange)})`;
  if (requestsColLabelEl) requestsColLabelEl.textContent = `Requests (${rangeLabel(selectedRange)})`;

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
      `Metrics shown from placeholder internal API (${rangeLabel(selectedRange)} range). Add per-tenant filtering and real charts after auth wiring.`;
  }

  setActiveMetricsRange(selectedRange);
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

async function selectMetricsRange(range) {
  const selected = setMetricsRange(range);
  setActiveMetricsRange(selected);
  const tableBody = document.getElementById("metrics-table-body");
  if (tableBody) {
    tableBody.innerHTML = '<tr><td colspan="4" class="small">Loading placeholder endpoint metrics…</td></tr>';
  }

  try {
    const payload = await loadOverviewPayload(selected);
    renderMetrics(payload);
  } catch (error) {
    renderMetricsError(error);
  }
}

async function loadActivityPayload() {
  const response = await fetch("/internal/api/activity", { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`activity request failed (${response.status})`);
  }
  return response.json();
}

function activityBadge(status) {
  if (status === "success") return '<span class="badge ok">success</span>';
  if (status === "info") return '<span class="badge warn">info</span>';
  return `<span class="badge">${status || "unknown"}</span>`;
}

function renderActivity(payload) {
  const tableBody = document.getElementById("activity-table-body");
  const calloutEl = document.getElementById("activity-callout");

  if (tableBody && Array.isArray(payload.events)) {
    tableBody.innerHTML = "";
    payload.events.forEach((event) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${new Date(event.timestamp).toLocaleString()}</td>
        <td>${event.actor || "system"}</td>
        <td>${event.action || "—"}</td>
        <td>${activityBadge(event.status)}</td>
        <td>${event.target || "—"}</td>
      `;
      tableBody.appendChild(row);
    });
  }

  if (calloutEl) {
    calloutEl.textContent =
      "Loaded from /internal/api/activity placeholder feed. Wire audit source + filters in next milestone.";
  }
}

function renderActivityError(error) {
  const tableBody = document.getElementById("activity-table-body");
  const calloutEl = document.getElementById("activity-callout");

  if (tableBody) {
    tableBody.innerHTML = `<tr><td colspan="5" class="small">Failed to load activity: ${error.message}</td></tr>`;
  }

  if (calloutEl) {
    calloutEl.textContent = "Could not load placeholder activity payload.";
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

  if (page === "overview") {
    try {
      const payload = await loadOverviewPayload("24h");
      renderOverview(payload);
    } catch {
      const calloutEl = document.getElementById("overview-callout");
      if (calloutEl) calloutEl.textContent = "Could not load placeholder summary.";
    }
  }

  if (page === "metrics") {
    const selectedRange = getMetricsRange();
    setActiveMetricsRange(selectedRange);
    await selectMetricsRange(selectedRange);
  }

  if (page === "activity") {
    try {
      const payload = await loadActivityPayload();
      renderActivity(payload);
    } catch (error) {
      renderActivityError(error);
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
  selectMetricsRange,
};
