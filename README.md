# Y Finance API (MVP)

Expose `yfinance` as a paid API for no-code builders.

## MVP Features
- REST API (FastAPI)
- Quote endpoint
- Historical candles endpoint
- Batch quotes endpoint
- Fundamentals endpoint
- API key auth (MVP master key mode)
- Stripe webhook skeleton for subscription sync
- OpenAPI docs at `/docs`

## Quick Start

```bash
cd yf-api-saas
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set API_MASTER_KEY in .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test

```bash
curl -H "x-api-key: replace-me" http://localhost:8000/v1/quote/AAPL
curl -H "x-api-key: replace-me" "http://localhost:8000/v1/history/AAPL?period=1mo&interval=1d"
curl -H "x-api-key: replace-me" "http://localhost:8000/v1/quotes?symbols=AAPL,MSFT,TSLA"
```

## Docker quick start

```bash
cp .env.example .env
# set API_MASTER_KEY in .env
docker compose up --build
```

## Next Required Steps
1. Replace master-key auth with per-user API keys stored in DB.
2. Add subscription state model and Stripe customer mapping.
3. Add rate limiting per key.
4. Add cache for expensive endpoints.
5. Add production deployment + CI/CD + uptime monitoring.

## Legal/Policy Note
This service wraps third-party market data access via `yfinance` and Yahoo Finance endpoints. Review terms and compliance requirements before commercialization.
