# Y Finance API (MVP)

Yahoo Finance data API for no-code builders (Zapier, Make, n8n, custom HTTP clients).

## First 15 minutes

### 1) Set up env + run API

```bash
cd yf-api-saas
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `API_MASTER_KEY` (required for protected endpoints)
- `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID_MONTHLY`, `STRIPE_WEBHOOK_SECRET` (only if using billing endpoints)

Start server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Base URL (local): `http://localhost:8000`

### 2) Make your first authenticated request

```bash
export API_KEY="replace-with-your-API_MASTER_KEY"

curl -sS -H "x-api-key: $API_KEY" \
  http://localhost:8000/v1/quote/AAPL
```

Expected: JSON with `symbol`, price fields, and `stale` flag.

### 3) Find key endpoints quickly

- Live docs (OpenAPI UI): `GET /docs`
- Error contract checklist: `docs/ERROR_CONTRACT_CHECKLIST.md`
- Billing safety checklist: `docs/BILLING_SAFETY_CHECKLIST.md`
- Test run matrix + marker lanes: `docs/TEST_RUN_MATRIX.md`
- Deployed smoke pack: `docs/DEPLOYED_SMOKE.md`
- Health: `GET /v1/health`
- Quote: `GET /v1/quote/{symbol}`
- History: `GET /v1/history/{symbol}?period=1mo&interval=1d`
- Batch quotes: `GET /v1/quotes?symbols=AAPL,MSFT,TSLA` (max 25)
- Fundamentals: `GET /v1/fundamentals/{symbol}`
- Billing plans: `GET /v1/billing/plans`
- Stripe checkout: `POST /v1/billing/checkout/session`
- Stripe webhook: `POST /v1/billing/webhook/stripe`

## Common errors (what to do)

- **401 Unauthorized**: missing/invalid `x-api-key`.
  - Action: send `x-api-key` header and verify key matches `API_MASTER_KEY` or `API_VALID_KEYS`.
- **402 Payment Required**: not currently returned by this API.
  - Action: if you enforce plan limits in your own gateway later, use 402 there.
- **422 Unprocessable Entity**: request shape/type validation failed (FastAPI/Pydantic), commonly in billing payloads.
  - Action: fix JSON/body fields and formats (valid email, valid URLs, required fields present).
- **429 Too Many Requests**: not currently emitted by built-in routes.
  - Action: if deployed behind a rate-limiter, back off and retry with jitter.
- **500 Internal Server Error**: unexpected server failure.
  - Action: retry once for idempotent reads; if persistent, check logs.
- **502 Bad Gateway**: upstream provider failure (Yahoo/Stripe).
  - Action: retry with backoff; treat as transient.

Also commonly seen in current routes:
- **400 Bad Request**: invalid symbol/period/interval/date range, malformed webhook/signature.
- **404 Not Found**: symbol/data unavailable.
- **503 Service Unavailable**: Stripe environment vars missing for billing endpoints.

## Docker quick start

```bash
cp .env.example .env
# set API_MASTER_KEY (and Stripe vars if using billing endpoints)
docker compose up --build
```

## Customer dashboard

Customer dashboard route:

- `/dashboard/`

Customer dashboard APIs:
- `/dashboard/api/session/login`
- `/dashboard/api/session/me`
- `/dashboard/api/session/logout`
- `/dashboard/api/overview?range=24h|7d|30d`
- `/dashboard/api/metrics?range=24h|7d|30d`
- `/dashboard/api/keys` + create/rotate/revoke/activate
- `/dashboard/api/activity`

See `docs/CUSTOMER_DASHBOARD.md` for current behavior and local/dev notes.

## Legal note

This service wraps third-party market data (`yfinance` / Yahoo Finance endpoints). Review provider terms/compliance before commercial use.

Not investment advice.
