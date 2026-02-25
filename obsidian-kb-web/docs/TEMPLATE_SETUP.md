---
type: guide
project: obsidian-knowledge-base
status: active
owner: Alfred
created: 2026-02-25
updated: 2026-02-25
---

# Obsidian Template Setup & Validation (MVP)

Use this once per local vault to make sure the starter templates are actually usable.

## Goal
Enable fast note creation using files in:
- `templates/project-note.md`
- `templates/meeting-note.md`
- `templates/knowledge-note.md`

## Option A (recommended MVP): Core Templates plugin

1. Open **Settings → Core plugins**.
2. Ensure **Templates** is enabled.
3. Open **Settings → Templates**.
4. Set **Template folder location** to `templates`.
5. Create a test note in `01_PROJECTS/`.
6. Run command: **Templates: Insert template**.
7. Select `project-note` and confirm the note is populated.

## Option B (optional): Templater plugin

Use only if you already rely on Templater workflows.

1. Open **Settings → Community plugins → Templater**.
2. Set **Template folder location** to `templates`.
3. Keep this repo's templates compatible with basic insertion first; avoid plugin-specific complexity unless needed.

## 3-minute Validation Checklist

- [ ] `project-note.md` inserts without manual cleanup.
- [ ] `meeting-note.md` inserts in `04_MEETINGS/`.
- [ ] `knowledge-note.md` inserts in `03_KNOWLEDGE/`.
- [ ] Inserted note has at least one internal link before save/commit.

## Record the Result (required)
After each local validation run, add one line to:
- `SETUP_VALIDATION_LOG.md`

Use this compact format:
- `YYYY-MM-DD | <machine/context> | <Core Templates|Templater> | <Pass|Fail> | <notes>`

This prevents repeated re-checks and makes machine-specific setup issues visible.

## Troubleshooting

- If template files do not appear in picker:
  - Verify folder path is exactly `templates` (lowercase).
  - Confirm files end with `.md`.
  - Restart Obsidian after plugin/path changes.
- If date/title placeholders do not render:
  - Verify template was inserted via Templates/Templater command, not copy-pasted manually.
