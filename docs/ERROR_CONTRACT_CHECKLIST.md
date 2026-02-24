# Error Contract Checklist (Endpoint-by-Endpoint)

Last validated: 2026-02-24
Validation source: automated pytest suite (`tests/test_api_auth_and_health.py`, `tests/test_api_market.py`, `tests/test_api_edge_cases.py`, `tests/test_api_billing.py`) — latest run: `67 passed` (`reports/test_report_2026-02-24_19-34-18.txt`).

## Standard envelope today
- `HTTPException` responses: `{ "detail": "..." }`
- Validation errors (422): `{ "detail": "Validation failed", "errors": [ ... ] }`

> Note: Error body shape is now normalized around a string `detail` field for all handled error cases.
>
> Auth precedence is explicitly regression-tested: protected market endpoints return `401` for missing/invalid API keys before malformed query/path validation details are exposed.

## Market + auth

| Endpoint | Scenarios checked | Expected status | Body shape | Result |
|---|---|---:|---|---|
| `GET /v1/health` | healthy service | 200 | `{ok:true}` | PASS |
| `GET /v1/quote/{symbol}` | missing key / bad key / malformed symbol / upstream crash / unknown symbol | 401 / 400 / 502 / 404 | `detail: string` | PASS |
| `GET /v1/history/{symbol}` | missing key / invalid key / malformed symbol / invalid period / invalid interval / bad date format / start>end / empty data / upstream crash | 401 / 400 / 422 / 404 / 502 | `detail: string` (+ `errors` list for 422) | PASS |
| `GET /v1/quotes` | missing key / invalid key / missing symbols / invalid symbol / over limit / malformed symbols list | 401 / 422 / 400 | `detail: string` (+ `errors` list for 422) | PASS |
| `GET /v1/fundamentals/{symbol}` | missing key / bad key / malformed symbol / no fundamentals / upstream crash | 401 / 400 / 404 / 502 | `detail: string` | PASS |

## Billing

| Endpoint | Scenarios checked | Expected status | Body shape | Result |
|---|---|---:|---|---|
| `GET /v1/billing/plans` | list plans | 200 | `{plans:[...]}` | PASS |
| `POST /v1/billing/checkout/session` | invalid payload / disallowed redirect / stripe not configured / stripe upstream failure | 422 / 503 / 502 | `detail: string` (+ `errors` list for 422) | PASS |
| `POST /v1/billing/webhook/stripe` | missing signature / invalid signature / webhook secret not configured | 400 / 503 | `detail: string` | PASS |

## Follow-up gap (not blocking)
- Consider adding stable machine-readable `error.code` values (while keeping `detail`) to simplify client-side branching across 400/401/404/422/502/503.
