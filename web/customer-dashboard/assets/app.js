import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import {
  Button,
  Card,
  FormRow,
  Grid,
  Input,
  Notice,
  RequestTrendChart,
  SegmentControl,
  Select,
  Shell,
  Table,
} from "./ui.js";
import {
  clearStoredSession,
  createKey,
  getActivity,
  getCustomerSession,
  getKeys,
  getMetrics,
  getOverview,
  keyAction,
  loginCustomerSession,
  registerCustomerSession,
  logoutCustomerSession,
  readStoredSession,
  storeSession,
} from "./api.js";

const navItems = [
  { key: "overview", label: "Overview" },
  { key: "keys", label: "API Keys" },
  { key: "metrics", label: "Metrics" },
  { key: "activity", label: "Activity" },
];

const DEFAULT_RANGE = "24h";
const validRanges = new Set(["24h", "7d", "30d"]);
const validActivityStatuses = new Set(["", "success", "info", "error"]);
const validKeyStatuses = new Set(["all", "active", "revoked"]);
const validKeyEnvironments = new Set(["all", "live", "test"]);
const DEFAULT_ACTIVITY_FILTERS = {
  status: "",
  action: "",
  limit: "25",
};
const DEFAULT_KEY_FILTERS = {
  q: "",
  status: "all",
  env: "all",
};

const normalizeRange = (value) => (validRanges.has(value) ? value : null);
const isAnalyticsRoute = (route) => route === "overview" || route === "metrics";

const normalizeActivityStatus = (value) =>
  validActivityStatuses.has(value ?? "") ? value ?? "" : DEFAULT_ACTIVITY_FILTERS.status;

const normalizeActivityLimit = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_ACTIVITY_FILTERS.limit;
  }

  return String(Math.min(100, Math.floor(parsed)));
};

const normalizeKeyStatus = (value) =>
  validKeyStatuses.has(value ?? DEFAULT_KEY_FILTERS.status) ? value ?? DEFAULT_KEY_FILTERS.status : DEFAULT_KEY_FILTERS.status;

const normalizeKeyEnvironment = (value) =>
  validKeyEnvironments.has(value ?? DEFAULT_KEY_FILTERS.env) ? value ?? DEFAULT_KEY_FILTERS.env : DEFAULT_KEY_FILTERS.env;

const readKeyFilters = (search) => {
  const params = new URLSearchParams(search);

  return {
    q: params.get("q") ?? DEFAULT_KEY_FILTERS.q,
    status: normalizeKeyStatus(params.get("status") ?? DEFAULT_KEY_FILTERS.status),
    env: normalizeKeyEnvironment(params.get("env") ?? DEFAULT_KEY_FILTERS.env),
  };
};

const sameKeyFilters = (left, right) => left.q === right.q && left.status === right.status && left.env === right.env;

const buildKeyFilterParams = (filters) => {
  const params = new URLSearchParams();

  if (filters.q.trim()) params.set("q", filters.q.trim());
  if (filters.status !== DEFAULT_KEY_FILTERS.status) params.set("status", filters.status);
  if (filters.env !== DEFAULT_KEY_FILTERS.env) params.set("env", filters.env);

  return params;
};

const readActivityFilters = (search) => {
  const params = new URLSearchParams(search);

  return {
    status: normalizeActivityStatus(params.get("status") ?? ""),
    action: (params.get("action") ?? "").trim(),
    limit: normalizeActivityLimit(params.get("limit") ?? DEFAULT_ACTIVITY_FILTERS.limit),
  };
};

const sameActivityFilters = (left, right) =>
  left.status === right.status && left.action === right.action && left.limit === right.limit;

const buildActivityParams = (filters) => {
  const params = new URLSearchParams();

  if (filters.status) params.set("status", filters.status);
  if (filters.action.trim()) params.set("action", filters.action.trim());
  if (filters.limit !== DEFAULT_ACTIVITY_FILTERS.limit) params.set("limit", filters.limit);

  return params;
};

const buildActivityFilterSummary = (filters) => {
  const normalizedStatus = normalizeActivityStatus(filters.status);
  const normalizedAction = (filters.action ?? "").trim();
  const normalizedLimit = normalizeActivityLimit(filters.limit);

  return {
    status: normalizedStatus || "all",
    action: normalizedAction || "any",
    limit: normalizedLimit,
  };
};

const csvEscape = (value) => {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }

  return text;
};

const buildActivityCsv = (events) => {
  const headers = ["timestamp", "actor", "action", "status", "target"];
  const lines = events.map((event) => headers.map((key) => csvEscape(event?.[key])).join(","));
  return [headers.join(","), ...lines].join("\n");
};

const downloadActivityCsv = (events) => {
  if (!events.length) {
    return;
  }

  const blob = new Blob([buildActivityCsv(events)], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  link.href = url;
  link.download = `activity-${stamp}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const isUnauthorizedError = (err) => err?.status === 401;

function useHashRoute() {
  const readLocation = () => {
    const hash = window.location.hash.replace(/^#/, "");
    const [path = "", search = ""] = hash.split("?");
    const route = path.replace(/^\/?/, "");

    return {
      route: navItems.some((item) => item.key === route) ? route : "overview",
      search,
    };
  };

  const [location, setLocation] = useState(readLocation);

  useEffect(() => {
    const onHash = () => setLocation(readLocation());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = (nextRoute, nextParams, { replace = false } = {}) => {
    const params =
      nextParams instanceof URLSearchParams
        ? nextParams
        : nextParams
        ? new URLSearchParams(nextParams)
        : null;
    const query = params?.toString();
    const nextHash = `/${nextRoute}${query ? `?${query}` : ""}`;

    if (replace) {
      const { pathname, search } = window.location;
      window.history.replaceState(null, "", `${pathname}${search}#${nextHash}`);
      setLocation(readLocation());
      return;
    }

    window.location.hash = nextHash;
  };

  return [location, navigate];
}

function OverviewPage({ range, setRange, onUnauthorized }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setError("");
    getOverview(range)
      .then((payload) => {
        if (active) setData(payload);
      })
      .catch((err) => {
        if (!active) return;
        if (isUnauthorizedError(err)) {
          onUnauthorized?.();
          return;
        }
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [range]);

  return React.createElement(
    React.Fragment,
    null,
    React.createElement(SegmentControl, {
      value: range,
      onChange: setRange,
      options: [
        { value: "24h", label: "24h" },
        { value: "7d", label: "7d" },
        { value: "30d", label: "30d" },
      ],
    }),
    error ? React.createElement(Notice, { tone: "error" }, error) : null,
    data
      ? React.createElement(
          React.Fragment,
          null,
          React.createElement(
            Grid,
            null,
            React.createElement(Card, {
              title: "Requests",
              value: data.requests.toLocaleString(),
              meta: `Range: ${data.range}`,
            }),
            React.createElement(Card, {
              title: "5xx Errors",
              value: String(data.fiveXx),
              meta: "Server-side failures",
            }),
            React.createElement(Card, {
              title: "Error rate",
              value: `${data.errorRatePct}%`,
              meta: "Across all endpoints",
            }),
            React.createElement(Card, {
              title: "P95 latency",
              value: `${data.p95LatencyMs} ms`,
              meta: "Response latency",
            })
          ),
          React.createElement(Card, {
            title: "Top endpoints",
            children: React.createElement(Table, {
              columns: [
                { key: "path", label: "Path" },
                { key: "requests", label: "Requests" },
                { key: "errorPct", label: "Error %" },
                { key: "p95Ms", label: "P95 ms" },
              ],
              rows: data.topEndpoints,
            }),
          })
        )
      : React.createElement(Notice, null, "Loading overview…")
  );
}

function KeysPage({ search, onUpdateSearch, onUnauthorized }) {
  const initialFilters = useMemo(() => readKeyFilters(search), [search]);
  const [keys, setKeys] = useState([]);
  const [label, setLabel] = useState("");
  const [env, setEnv] = useState("test");
  const [query, setQuery] = useState(initialFilters.q);
  const [statusFilter, setStatusFilter] = useState(initialFilters.status);
  const [envFilter, setEnvFilter] = useState(initialFilters.env);
  const [pendingAction, setPendingAction] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const nextFilters = readKeyFilters(search);
    const currentFilters = {
      q: query,
      status: statusFilter,
      env: envFilter,
    };

    if (sameKeyFilters(currentFilters, nextFilters)) {
      return;
    }

    setQuery(nextFilters.q);
    setStatusFilter(nextFilters.status);
    setEnvFilter(nextFilters.env);
  }, [search]);

  useEffect(() => {
    const normalizedFilters = {
      q: query,
      status: normalizeKeyStatus(statusFilter),
      env: normalizeKeyEnvironment(envFilter),
    };
    const nextParams = buildKeyFilterParams(normalizedFilters);
    const currentParams = buildKeyFilterParams(readKeyFilters(search));

    if (nextParams.toString() === currentParams.toString()) {
      return;
    }

    onUpdateSearch(nextParams);
  }, [query, statusFilter, envFilter, search, onUpdateSearch]);

  const load = () =>
    getKeys()
      .then((payload) => setKeys(payload.keys))
      .catch((err) => {
        if (isUnauthorizedError(err)) {
          onUnauthorized?.();
          return;
        }
        setError(err.message);
      });

  useEffect(() => {
    load();
  }, []);

  const submitCreate = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await createKey(label, env);
      setLabel("");
      setMessage("Key created.");
      await load();
    } catch (err) {
      if (isUnauthorizedError(err)) {
        onUnauthorized?.();
        return;
      }
      setError(err.message);
    }
  };

  const onAction = async (id, action) => {
    if (action === "revoke") {
      const confirmed = window.confirm("Revoke this key now? Existing integrations using this key will stop working.");
      if (!confirmed) {
        return;
      }
    }

    setPendingAction(`${id}:${action}`);
    setError("");
    setMessage("");
    try {
      await keyAction(id, action);
      setMessage(`Key ${action} complete.`);
      await load();
    } catch (err) {
      if (isUnauthorizedError(err)) {
        onUnauthorized?.();
        return;
      }
      setError(err.message);
    } finally {
      setPendingAction("");
    }
  };

  const normalizedQuery = query.trim().toLowerCase();

  const filteredKeys = useMemo(
    () =>
      keys.filter((key) => {
        const matchesQuery =
          !normalizedQuery ||
          key.label.toLowerCase().includes(normalizedQuery) ||
          key.prefix.toLowerCase().includes(normalizedQuery) ||
          key.id.toLowerCase().includes(normalizedQuery);
        const matchesStatus =
          statusFilter === "all" || (statusFilter === "active" ? key.active : !key.active);
        const matchesEnv = envFilter === "all" || key.env === envFilter;

        return matchesQuery && matchesStatus && matchesEnv;
      }),
    [keys, normalizedQuery, statusFilter, envFilter]
  );

  const summary = useMemo(() => {
    const activeCount = keys.filter((key) => key.active).length;
    const revokedCount = keys.length - activeCount;
    const liveCount = keys.filter((key) => key.env === "live").length;
    const testCount = keys.length - liveCount;
    return { activeCount, revokedCount, liveCount, testCount };
  }, [keys]);

  const rows = useMemo(
    () =>
      filteredKeys.map((key) => {
        const rotatePending = pendingAction === `${key.id}:rotate`;
        const revokePending = pendingAction === `${key.id}:revoke`;
        const activatePending = pendingAction === `${key.id}:activate`;

        return {
          ...key,
          prefix: React.createElement("code", { className: "key-prefix" }, key.prefix),
          active: React.createElement(
            "span",
            { className: `status-pill ${key.active ? "active" : "revoked"}` },
            key.active ? "active" : "revoked"
          ),
          actions: React.createElement(
            "div",
            { className: "row-actions" },
            React.createElement(
              Button,
              {
                tone: "muted",
                onClick: () => onAction(key.id, "rotate"),
                disabled: Boolean(pendingAction),
              },
              rotatePending ? "Rotating…" : "Rotate"
            ),
            key.active
              ? React.createElement(
                  Button,
                  {
                    tone: "danger",
                    onClick: () => onAction(key.id, "revoke"),
                    disabled: Boolean(pendingAction),
                  },
                  revokePending ? "Revoking…" : "Revoke"
                )
              : React.createElement(
                  Button,
                  {
                    tone: "success",
                    onClick: () => onAction(key.id, "activate"),
                    disabled: Boolean(pendingAction),
                  },
                  activatePending ? "Activating…" : "Activate"
                )
          ),
        };
      }),
    [filteredKeys, pendingAction]
  );

  return React.createElement(
    React.Fragment,
    null,
    React.createElement(
      Card,
      { title: "Create API key" },
      React.createElement(
        "form",
        { onSubmit: submitCreate },
        React.createElement(
          FormRow,
          null,
          React.createElement(Input, {
            placeholder: "Label",
            value: label,
            onChange: (e) => setLabel(e.target.value),
            required: true,
          }),
          React.createElement(
            Select,
            {
              value: env,
              onChange: (e) => setEnv(e.target.value),
            },
            React.createElement("option", { value: "test" }, "test"),
            React.createElement("option", { value: "live" }, "live")
          ),
          React.createElement(Button, { type: "submit", tone: "primary", disabled: Boolean(pendingAction) }, "Create")
        )
      )
    ),
    message ? React.createElement(Notice, { tone: "success" }, message) : null,
    error ? React.createElement(Notice, { tone: "error" }, error) : null,
    React.createElement(
      Grid,
      null,
      React.createElement(Card, { title: "Total keys", value: String(keys.length), meta: "Across all environments" }),
      React.createElement(Card, { title: "Active", value: String(summary.activeCount), meta: "Ready for requests" }),
      React.createElement(Card, { title: "Revoked", value: String(summary.revokedCount), meta: "Disabled keys" }),
      React.createElement(Card, {
        title: "Environment split",
        value: `${summary.liveCount} live · ${summary.testCount} test`,
        meta: "Current inventory",
      })
    ),
    React.createElement(
      Card,
      { title: "API keys" },
      React.createElement(
        FormRow,
        null,
        React.createElement(Input, {
          placeholder: "Search label, prefix, or id",
          value: query,
          onChange: (e) => setQuery(e.target.value),
        }),
        React.createElement(
          Select,
          { value: statusFilter, onChange: (e) => setStatusFilter(e.target.value) },
          React.createElement("option", { value: "all" }, "All statuses"),
          React.createElement("option", { value: "active" }, "Active"),
          React.createElement("option", { value: "revoked" }, "Revoked")
        ),
        React.createElement(
          Select,
          { value: envFilter, onChange: (e) => setEnvFilter(e.target.value) },
          React.createElement("option", { value: "all" }, "All environments"),
          React.createElement("option", { value: "live" }, "live"),
          React.createElement("option", { value: "test" }, "test")
        ),
        React.createElement(
          Button,
          {
            tone: "muted",
            onClick: () => {
              setQuery(DEFAULT_KEY_FILTERS.q);
              setStatusFilter(DEFAULT_KEY_FILTERS.status);
              setEnvFilter(DEFAULT_KEY_FILTERS.env);
            },
            disabled:
              query === DEFAULT_KEY_FILTERS.q &&
              statusFilter === DEFAULT_KEY_FILTERS.status &&
              envFilter === DEFAULT_KEY_FILTERS.env,
          },
          "Clear"
        )
      ),
      React.createElement(Table, {
        columns: [
          { key: "label", label: "Label" },
          { key: "prefix", label: "Prefix" },
          { key: "env", label: "Env" },
          { key: "active", label: "Status" },
          { key: "lastUsed", label: "Last used" },
          { key: "actions", label: "Actions" },
        ],
        rows,
      }),
      React.createElement(
        "p",
        { className: "card-meta" },
        `${filteredKeys.length} of ${keys.length} keys shown`
      )
    )
  );
}

function MetricsPage({ range, setRange, onUnauthorized }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    getMetrics(range)
      .then((payload) => {
        if (!active) return;
        setData(payload);
      })
      .catch((err) => {
        if (!active) return;
        if (isUnauthorizedError(err)) {
          onUnauthorized?.();
          return;
        }
        setError(err.message);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [range]);

  return React.createElement(
    React.Fragment,
    null,
    React.createElement(Card, {
      title: "Usage & Metrics",
      meta: "Placeholder analytics API · live range view",
      children: React.createElement(SegmentControl, {
        value: range,
        onChange: setRange,
        options: [
          { value: "24h", label: "24h" },
          { value: "7d", label: "7d" },
          { value: "30d", label: "30d" },
        ],
      }),
    }),
    error ? React.createElement(Notice, { tone: "error" }, error) : null,
    loading ? React.createElement(Notice, null, "Loading usage metrics…") : null,
    !loading && data
      ? React.createElement(
          React.Fragment,
          null,
          React.createElement(
            Grid,
            null,
            React.createElement(Card, {
              title: "P95 latency",
              value: `${data.summary.p95LatencyMs} ms`,
              meta: `Range: ${data.range}`,
            }),
            React.createElement(Card, {
              title: "5xx count",
              value: String(data.summary.fiveXx),
              meta: "Server-side failures",
            }),
            React.createElement(Card, {
              title: "Error rate",
              value: `${data.summary.errorRatePct}%`,
              meta: "Across all endpoints",
            }),
            React.createElement(Card, {
              title: "Requests",
              value: data.summary.requests.toLocaleString(),
              meta: "Total requests",
            })
          ),
          React.createElement(Card, {
            title: "Request trend",
            meta: "Requests per time bucket",
            children: React.createElement(RequestTrendChart, {
              points: data.requestTrend,
              ariaLabel: `Request trend for ${data.range}`,
            }),
          }),
          React.createElement(Card, {
            title: "Status code breakdown",
            children: React.createElement(Table, {
              columns: [
                { key: "status", label: "Status" },
                { key: "requests", label: "Requests" },
                { key: "pct", label: "Share %" },
              ],
              rows: data.statusBreakdown,
            }),
          }),
          React.createElement(Card, {
            title: "Latency buckets",
            children: React.createElement(Table, {
              columns: [
                { key: "bucket", label: "Bucket" },
                { key: "requests", label: "Requests" },
                { key: "pct", label: "Share %" },
              ],
              rows: data.latencyBuckets,
            }),
          }),
          React.createElement(Card, {
            title: "Top endpoints by requests",
            children: React.createElement(Table, {
              columns: [
                { key: "method", label: "Method" },
                { key: "path", label: "Path" },
                { key: "requests", label: "Requests" },
                { key: "errorPct", label: "Error %" },
                { key: "p95Ms", label: "P95 ms" },
              ],
              rows: data.topEndpoints,
            }),
          })
        )
      : null
  );
}

function ActivityPage({ search, onUpdateSearch, onUnauthorized }) {
  const initialFilters = useMemo(() => readActivityFilters(search), [search]);
  const [events, setEvents] = useState([]);
  const [draftFilters, setDraftFilters] = useState(initialFilters);
  const [appliedFilters, setAppliedFilters] = useState(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");
  const [refreshCounter, setRefreshCounter] = useState(0);

  useEffect(() => {
    const nextFilters = readActivityFilters(search);
    setDraftFilters((current) => (sameActivityFilters(current, nextFilters) ? current : nextFilters));
    setAppliedFilters((current) => (sameActivityFilters(current, nextFilters) ? current : nextFilters));
  }, [search]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    const parsedLimit = Number(appliedFilters.limit);
    getActivity({
      status: appliedFilters.status || undefined,
      action: appliedFilters.action.trim() || undefined,
      limit: Number.isFinite(parsedLimit) && parsedLimit > 0 ? parsedLimit : undefined,
    })
      .then((payload) => {
        if (!active) return;
        setEvents(payload.events);
        setLastUpdated(new Date().toLocaleString());
      })
      .catch((err) => {
        if (!active) return;
        if (isUnauthorizedError(err)) {
          onUnauthorized?.();
          return;
        }
        setError(err.message);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [appliedFilters, refreshCounter]);

  const setDraftField = (field, value) => {
    setDraftFilters((current) => ({ ...current, [field]: value }));
  };

  const applyFilters = () => {
    const nextFilters = {
      status: normalizeActivityStatus(draftFilters.status),
      action: draftFilters.action.trim(),
      limit: normalizeActivityLimit(draftFilters.limit),
    };

    setDraftFilters(nextFilters);
    setAppliedFilters(nextFilters);
    onUpdateSearch(buildActivityParams(nextFilters));
  };

  const resetFilters = () => {
    setDraftFilters(DEFAULT_ACTIVITY_FILTERS);
    setAppliedFilters(DEFAULT_ACTIVITY_FILTERS);
    onUpdateSearch(new URLSearchParams());
  };

  const hasPendingChanges = !sameActivityFilters(draftFilters, appliedFilters);

  const filterSummary = useMemo(() => buildActivityFilterSummary(appliedFilters), [appliedFilters]);

  const renderedEvents = useMemo(
    () =>
      events.map((event) => ({
        ...event,
        status: React.createElement(
          "span",
          { className: `status-pill ${normalizeActivityStatus(event.status) || "info"}` },
          event.status
        ),
      })),
    [events]
  );

  const hasNoEvents = !loading && !error && renderedEvents.length === 0;

  return React.createElement(
    React.Fragment,
    null,
    React.createElement(
      Card,
      { title: "Activity filters" },
      React.createElement(
        FormRow,
        null,
        React.createElement(
          Select,
          { value: draftFilters.status, onChange: (e) => setDraftField("status", e.target.value) },
          React.createElement("option", { value: "" }, "All statuses"),
          React.createElement("option", { value: "success" }, "success"),
          React.createElement("option", { value: "info" }, "info"),
          React.createElement("option", { value: "error" }, "error")
        ),
        React.createElement(Input, {
          placeholder: "Filter action contains…",
          value: draftFilters.action,
          onChange: (e) => setDraftField("action", e.target.value),
        }),
        React.createElement(
          Select,
          { value: draftFilters.limit, onChange: (e) => setDraftField("limit", normalizeActivityLimit(e.target.value)) },
          React.createElement("option", { value: "10" }, "10"),
          React.createElement("option", { value: "25" }, "25"),
          React.createElement("option", { value: "50" }, "50"),
          React.createElement("option", { value: "100" }, "100")
        ),
        React.createElement(Input, {
          type: "number",
          min: 1,
          max: 100,
          value: draftFilters.limit,
          onChange: (e) => setDraftField("limit", e.target.value),
          placeholder: "Limit",
        }),
        React.createElement(
          Button,
          { tone: "primary", onClick: applyFilters, disabled: !hasPendingChanges },
          "Apply"
        ),
        React.createElement(Button, { tone: "muted", onClick: resetFilters }, "Reset"),
        React.createElement(Button, { tone: "muted", onClick: () => setRefreshCounter((value) => value + 1) }, "Refresh")
      )
    ),
    error ? React.createElement(Notice, { tone: "error" }, error) : null,
    loading ? React.createElement(Notice, null, "Loading activity…") : null,
    lastUpdated ? React.createElement("p", { className: "card-meta" }, `Last updated: ${lastUpdated}`) : null,
    React.createElement(
      Card,
      { title: "Recent activity" },
      React.createElement(
        "div",
        { className: "activity-summary" },
        React.createElement(
          "p",
          { className: "card-meta" },
          `Active filters: status=${filterSummary.status} · action=${filterSummary.action} · limit=${filterSummary.limit}`
        ),
        React.createElement(
          Button,
          {
            tone: "muted",
            onClick: () => downloadActivityCsv(events),
            disabled: !events.length,
          },
          "Export CSV"
        )
      ),
      hasNoEvents
        ? React.createElement(
            Notice,
            null,
            "No activity events matched the current filters. Try broadening status/action filters or increasing the limit."
          )
        : React.createElement(Table, {
            columns: [
              { key: "timestamp", label: "Timestamp" },
              { key: "actor", label: "Actor" },
              { key: "action", label: "Action" },
              { key: "status", label: "Status" },
              { key: "target", label: "Target" },
            ],
            rows: renderedEvents,
          })
    )
  );
}

function LoginPage({ onLogin, onRegister, pending, error }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submitLogin = async (event) => {
    event.preventDefault();
    await onLogin({ email, password });
  };

  const submitRegister = async () => {
    await onRegister({ email, password });
  };

  return React.createElement(
    "main",
    { className: "content" },
    React.createElement(
      Card,
      {
        title: "Customer dashboard sign in",
        meta: "Use your customer account email and password.",
      },
      React.createElement(
        "form",
        { onSubmit: submitLogin },
        React.createElement(
          FormRow,
          null,
          React.createElement(Input, {
            type: "email",
            placeholder: "you@company.com",
            value: email,
            onChange: (e) => setEmail(e.target.value),
            required: true,
          }),
          React.createElement(Input, {
            type: "password",
            placeholder: "Password",
            value: password,
            onChange: (e) => setPassword(e.target.value),
            minLength: 8,
            required: true,
          }),
          React.createElement(Button, { type: "submit", tone: "primary", disabled: pending }, pending ? "Signing in…" : "Sign in"),
          React.createElement(Button, { type: "button", tone: "muted", disabled: pending, onClick: submitRegister }, pending ? "Creating…" : "Create account")
        )
      ),
      error ? React.createElement(Notice, { tone: "error" }, error) : null
    )
  );
}

function App() {
  const [location, navigate] = useHashRoute();
  const route = location.route;
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const [range, setRange] = useState(() => normalizeRange(searchParams.get("range")) ?? DEFAULT_RANGE);
  const [session, setSession] = useState(() => readStoredSession());
  const [authLoading, setAuthLoading] = useState(true);
  const [authPending, setAuthPending] = useState(false);
  const [authError, setAuthError] = useState("");

  const clearAuth = () => {
    clearStoredSession();
    setSession(null);
    setAuthError("Your customer dashboard session ended. Please sign in again.");
  };

  useEffect(() => {
    const storedSession = readStoredSession();
    if (!storedSession?.token) {
      setAuthLoading(false);
      return;
    }

    getCustomerSession()
      .then((payload) => {
        const nextSession = payload?.session;
        if (nextSession?.token) {
          storeSession(nextSession);
          setSession(nextSession);
        }
      })
      .catch(() => {
        clearStoredSession();
        setSession(null);
      })
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    if (!isAnalyticsRoute(route)) {
      return;
    }

    const hashRange = normalizeRange(searchParams.get("range"));
    if (hashRange && hashRange !== range) {
      setRange(hashRange);
    }
  }, [route, searchParams, range]);

  useEffect(() => {
    if (!isAnalyticsRoute(route)) {
      return;
    }

    const hashRange = normalizeRange(searchParams.get("range"));
    if (hashRange === range) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("range", range);
    navigate(route, nextParams, { replace: true });
  }, [route, searchParams, range, navigate]);

  const onNavigate = (nextRoute) => {
    if (isAnalyticsRoute(nextRoute)) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.set("range", range);
      navigate(nextRoute, nextParams);
      return;
    }

    navigate(nextRoute);
  };

  const consumeAuthPayload = (payload) => {
    const nextSession = payload?.session;
    if (!nextSession?.token) {
      throw new Error("Session login failed");
    }
    storeSession(nextSession);
    setSession(nextSession);
  };

  const onLogin = async ({ email, password }) => {
    setAuthPending(true);
    setAuthError("");
    try {
      const payload = await loginCustomerSession(email, password);
      consumeAuthPayload(payload);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthPending(false);
      setAuthLoading(false);
    }
  };

  const onRegister = async ({ email, password }) => {
    setAuthPending(true);
    setAuthError("");
    try {
      const payload = await registerCustomerSession(email, password);
      consumeAuthPayload(payload);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthPending(false);
      setAuthLoading(false);
    }
  };

  const onLogout = async () => {
    try {
      await logoutCustomerSession();
    } catch (_err) {
      // Ignore logout transport errors and always clear local session state.
    }
    clearStoredSession();
    setSession(null);
    setAuthError("");
  };

  if (authLoading) {
    return React.createElement("main", { className: "content" }, React.createElement(Notice, null, "Checking customer dashboard session…"));
  }

  if (!session?.token) {
    return React.createElement(LoginPage, {
      onLogin,
      onRegister,
      pending: authPending,
      error: authError,
    });
  }

  const pageTitle = navItems.find((item) => item.key === route)?.label ?? "Overview";

  const page =
    route === "keys"
      ? React.createElement(KeysPage, {
          search: location.search,
          onUpdateSearch: (nextParams) => navigate("keys", nextParams),
          onUnauthorized: clearAuth,
        })
      : route === "metrics"
      ? React.createElement(MetricsPage, { range, setRange, onUnauthorized: clearAuth })
      : route === "activity"
      ? React.createElement(ActivityPage, {
          search: location.search,
          onUpdateSearch: (nextParams) => navigate("activity", nextParams),
          onUnauthorized: clearAuth,
        })
      : React.createElement(OverviewPage, { range, setRange, onUnauthorized: clearAuth });

  return React.createElement(
    Shell,
    {
      title: pageTitle,
      navItems,
      route,
      onNavigate,
    },
    React.createElement(
      Card,
      {
        title: "Customer session",
        meta: `${session.email} · ${session.tenantId}`,
      },
      React.createElement(Button, { tone: "muted", onClick: onLogout }, "Sign out")
    ),
    page
  );
}

createRoot(document.getElementById("root")).render(React.createElement(App));
