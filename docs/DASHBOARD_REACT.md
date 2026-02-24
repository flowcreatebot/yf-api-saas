# Internal Dashboard Migration (modern UI slice)

This repo serves two dashboard shells in parallel during migration:

- Primary dashboard: `/internal/dashboard/`
- Legacy compatibility shell: `/internal/dashboard-legacy/`

## Local dev

1) Run API server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2) Open dashboard:

- `http://localhost:8000/internal/dashboard/`

Current modern dashboard slice includes:
- Overview page wired to `/internal/api/overview?range=24h|7d|30d`
- API Keys page wired to `/internal/api/keys` and key lifecycle endpoints
- Activity page wired to `/internal/api/activity`
- Metrics placeholder page (navigable)

## Production mount plan

- Keep `/internal/dashboard/` as the primary route.
- Keep `/internal/dashboard-legacy/` for temporary backward compatibility.
- Once modern dashboard parity is fully verified, retire legacy shell in a later release.
