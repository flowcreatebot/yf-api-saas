# API Guide (MVP)

Base URL (local): `http://localhost:8000`

## First 15 minutes

1) **Set env + run**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Set at minimum in `.env`:
- `API_MASTER_KEY` for protected API calls
- Stripe vars only if using billing endpoints

2) **First successful authenticated call**

```bash
export API_KEY="replace-with-your-API_MASTER_KEY"
curl -sS -H "x-api-key: $API_KEY" http://localhost:8000/v1/quote/AAPL
```

3) **Where to find key endpoints**
- Interactive docs: `GET /docs`
- Market routes under `/v1/*`
- Billing routes under `/v1/billing/*`

---

## Authentication

Send API key in request header:

```http
x-api-key: YOUR_API_KEY
```

Auth behavior:
- Missing key → `401` (`"Missing API key"`)
- Invalid key → `401` (`"Invalid API key"`)

---

## Key endpoints

### Market
- `GET /v1/health`
- `GET /v1/quote/{symbol}`
- `GET /v1/history/{symbol}`
  - Query params: `period`, `interval`, optional `start`, `end`
- `GET /v1/quotes?symbols=AAPL,MSFT,TSLA` (max 25)
- `GET /v1/fundamentals/{symbol}`

Examples:

```bash
curl -H "x-api-key: $API_KEY" http://localhost:8000/v1/quote/AAPL
curl -H "x-api-key: $API_KEY" "http://localhost:8000/v1/history/TSLA?period=3mo&interval=1d"
curl -H "x-api-key: $API_KEY" "http://localhost:8000/v1/quotes?symbols=AAPL,MSFT,TSLA"
curl -H "x-api-key: $API_KEY" http://localhost:8000/v1/fundamentals/MSFT
```

### Billing
- `GET /v1/billing/plans`
- `POST /v1/billing/checkout/session`
- `POST /v1/billing/webhook/stripe`

Checkout request body:

```json
{
  "email": "user@example.com",
  "success_url": "https://yourapp.com/billing/success",
  "cancel_url": "https://yourapp.com/billing/cancel"
}
```

Notes:
- `success_url` and `cancel_url` must be HTTPS (localhost allowed for development).
- `BILLING_ALLOWED_REDIRECT_HOSTS` can further restrict redirect hosts.

---

## Common errors (status → action)

For endpoint-by-endpoint verification status, see `docs/ERROR_CONTRACT_CHECKLIST.md`.
For billing preflight and failure-mode checks, see `docs/BILLING_SAFETY_CHECKLIST.md`.

- **401 Unauthorized**: missing/invalid API key.
  - Action: include `x-api-key`; verify key against server env.
- **402 Payment Required**: not currently returned by built-in routes.
  - Action: if you add subscription enforcement externally, handle 402 in client flow.
- **422 Unprocessable Entity**: validation error (`detail: "Validation failed"` + `errors: [...]`).
  - Action: inspect `errors` and fix payload shape (especially billing email/URLs and required fields).
- **429 Too Many Requests**: not currently emitted by built-in routes.
  - Action: if your edge/gateway returns it, retry with exponential backoff + jitter.
- **500 Internal Server Error**: unexpected server issue.
  - Action: retry idempotent read once; then inspect server logs.
- **502 Bad Gateway**: upstream Yahoo/Stripe failure.
  - Action: retry with backoff; treat as transient.

Also used by current implementation:
- **400** invalid symbol/period/interval/date range, invalid webhook/signature
- **404** symbol/data unavailable
- **503** Stripe config missing for billing endpoints

---

## No-code integration pattern

1. Use HTTP module in Zapier/Make/n8n.
2. Add `x-api-key` header.
3. Call quote/history/fundamentals route.
4. Branch on status code:
   - retry: `502` (and `429` if your gateway emits it)
   - fix request/auth: `400/401/422`
   - treat as not-found/business outcome: `404`
5. Map JSON fields downstream.
