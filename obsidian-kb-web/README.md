# Obsidian KB Web (Password Protected)

Build docs with MkDocs and serve behind a simple login.

Required env vars:
- `KB_PASSWORD`
- `SESSION_SECRET`
Optional:
- `KB_USERNAME` (default: daniel)

Build command:
`pip install -r requirements.txt && mkdocs build`

Start command:
`gunicorn app:app --bind 0.0.0.0:$PORT`
