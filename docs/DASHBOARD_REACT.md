# Internal Dashboard Migration (modern UI slice)

Dashboard static shells are optional in this repo snapshot.

When static bundles are present:
- Primary dashboard: `/internal/dashboard/`
- Legacy compatibility shell: `/internal/dashboard-legacy/`

When static bundles are absent:
- `/internal` intentionally falls back to `/docs`
- Internal dashboard APIs under `/internal/api/*` remain active and tested

## Local dev

1) Run API server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2) Open dashboard:

- `http://localhost:8000/internal/dashboard/`

Current modern dashboard slice includes:
- Overview page wired to `/internal/api/overview?range=24h|7d|30d`
- Metrics page wired to `/internal/api/metrics?range=24h|7d|30d` with range selector, KPI cards, loading/error state, a request-trend chart from `requestTrend`, and structured metrics tables
- Overview + Metrics share one deep-linkable range selector (`24h`/`7d`/`30d`) across navigation and reload via hash query params (example: `/internal/dashboard/#/metrics?range=7d`)
- API Keys page wired to `/internal/api/keys` and key lifecycle endpoints, now with inventory KPI cards, table search/status/env filters, guarded revoke confirmation, and per-row action loading states
- Activity page wired to `/internal/api/activity` with filters for `status`, `action` contains, and `limit`

## Metrics endpoint contract (`GET /internal/api/metrics`)

Query params:
- `range`: one of `24h`, `7d`, `30d` (defaults to `24h`)

Payload shape used by the React Metrics page:

```json
{
  "range": "24h",
  "source": "placeholder",
  "summary": {
    "requests": 12842,
    "errorRatePct": 0.62,
    "p95LatencyMs": 184,
    "fiveXx": 9
  },
  "requestTrend": [
    { "bucket": "00:00", "requests": 1804 }
  ],
  "statusBreakdown": [
    { "status": "2xx", "requests": 12542, "pct": 97.66 }
  ],
  "latencyBuckets": [
    { "bucket": "0-100ms", "requests": 6010, "pct": 46.80 }
  ],
  "topEndpoints": [
    { "method": "GET", "path": "/v1/quote/{symbol}", "requests": 8120, "errorPct": 0.41, "p95Ms": 142 }
  ]
}
```

How the Metrics page uses it:
- KPI cards read `summary.{requests,errorRatePct,p95LatencyMs,fiveXx}`
- Range control (`24h`/`7d`/`30d`) re-fetches the endpoint
- Request trend chart renders `requestTrend` buckets (shows an empty-state note when no buckets exist)
- Tables render `statusBreakdown`, `latencyBuckets`, and `topEndpoints`
- Loading and error notices are shown around fetch lifecycle

## Legacy URL compatibility

To avoid breaking old bookmarks during cutover, React dashboard now serves lightweight compatibility entry pages:

- `/internal/dashboard/keys.html` → `/internal/dashboard/#/keys`
- `/internal/dashboard/metrics.html` → `/internal/dashboard/#/metrics`
- `/internal/dashboard/activity.html` → `/internal/dashboard/#/activity`
- `/internal/dashboard/overview.html` → `/internal/dashboard/#/overview`
- `/internal/dashboard/app.html` → `/internal/dashboard/#/overview`
- `/internal/dashboard/login.html` → `/internal/dashboard/#/overview`

Each page includes a JS redirect and a `<noscript>` fallback link.

## Production mount plan

- Keep `/internal/dashboard/` as the primary route.
- Keep `/internal/dashboard-legacy/` for temporary backward compatibility.
- Once modern dashboard parity is fully verified, retire legacy shell in a later release.
