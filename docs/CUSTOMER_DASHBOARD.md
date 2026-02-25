# Customer Dashboard

## Routes

- App: `/dashboard/`
- APIs: `/dashboard/api/*`

## Session endpoints

- `POST /dashboard/api/session/login`
- `GET /dashboard/api/session/me`
- `POST /dashboard/api/session/logout`

All dashboard API calls require a valid customer session (Bearer token or `X-Customer-Session`).

## Data endpoints

- `GET /dashboard/api/overview?range=24h|7d|30d`
- `GET /dashboard/api/metrics?range=24h|7d|30d`
- `GET /dashboard/api/activity?status=&action=&limit=`
- `GET /dashboard/api/keys`
- `POST /dashboard/api/keys/create`
- `POST /dashboard/api/keys/{id}/rotate`
- `POST /dashboard/api/keys/{id}/revoke`
- `POST /dashboard/api/keys/{id}/activate`

## Local dev

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# open http://localhost:8000/dashboard/
```

## Notes

Current dashboard data contracts are placeholder-backed and tenant-scoped by session metadata.
