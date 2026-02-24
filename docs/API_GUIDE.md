# API Guide (MVP)

Base URL (local): `http://localhost:8000`

Auth header:

```http
x-api-key: YOUR_KEY
```

## Endpoints

### GET `/v1/health`
Health check.

### GET `/v1/quote/{symbol}`
Current ticker snapshot.

Example:

```bash
curl -H "x-api-key: $API_KEY" http://localhost:8000/v1/quote/AAPL
```

### GET `/v1/history/{symbol}`
Historical OHLCV candles.

Query params:
- `period` (default `1mo`)
- `interval` (default `1d`)
- `start` (`YYYY-MM-DD`, optional)
- `end` (`YYYY-MM-DD`, optional)

Example:

```bash
curl -H "x-api-key: $API_KEY" "http://localhost:8000/v1/history/TSLA?period=3mo&interval=1d"
```

### GET `/v1/quotes?symbols=AAPL,MSFT,TSLA`
Batch quote fetch for up to 25 symbols in one request.

Example:

```bash
curl -H "x-api-key: $API_KEY" "http://localhost:8000/v1/quotes?symbols=AAPL,MSFT,TSLA"
```

### GET `/v1/fundamentals/{symbol}`
Basic company/fundamental fields.

Example:

```bash
curl -H "x-api-key: $API_KEY" http://localhost:8000/v1/fundamentals/MSFT
```

## Billing Endpoints

### GET `/v1/billing/plans`
Returns available plans.

### POST `/v1/billing/webhook/stripe`
Stripe webhook receiver (signature verification enabled when configured).

## No-Code Integration Pattern
1. Use HTTP module in Zapier/Make.
2. Add `x-api-key` header.
3. Call quote/history/fundamentals endpoint.
4. Map JSON response into downstream steps.
