---
type: workflow
project: obsidian-knowledge-base
status: draft
owner: Alfred
created: 2026-02-25
updated: 2026-02-25
---

# Obsidian Knowledge Base — Operating Workflow (MVP)

This is the default low-friction workflow for Boss + Alfred collaboration.

## 1) Daily Git Cadence (Manual CLI)

### Start of work session
```bash
git pull --rebase
```

### During session
- Make focused edits.
- Keep commits small and meaningful.
- Do not mix unrelated changes in one commit.

### End of work session
```bash
git status --short
git add projects/obsidian-knowledge-base
git commit -m "<clear summary>"
git push
```

Why this default: the workspace may contain other active projects, so path-scoped staging prevents accidental cross-project commits.

## 2) Note Lifecycle (Capture → Process → Link)

### Capture (fast)
- Write quick notes in the relevant project note or inbox note.
- Do not over-format while capturing.

### Process (same day if possible)
- Move raw notes into the correct folder.
- Add minimal frontmatter (title/date/tags when useful).
- Convert action items into explicit checklists.

### Link (make retrieval easy)
- Add at least one internal link from the note to:
  - parent project note, or
  - central index note.

## 3) Folder Usage (v1)
- `00_INDEX/` — maps and entry points.
- `01_PROJECTS/` — active project pages and support notes.
- `02_OPERATIONS/` — runbooks, SOPs, recurring procedures.
- `03_KNOWLEDGE/` — evergreen concepts/reference material.
- `04_MEETINGS/` — meeting notes and outcomes.
- `90_ARCHIVE/` — inactive/retired material.

## 4) Note Naming Conventions (MVP)
Keep names predictable so links/autocomplete stay clean.

- Use `kebab-case` filenames (lowercase words joined with `-`).
- Prefer concise names (3–7 words) with clear nouns.
- Avoid machine timestamps in titles unless chronology is the point.

By folder:
- `01_PROJECTS/` → `project-<name>.md` (example: `project-obsidian-kb.md`)
- `04_MEETINGS/` → `meeting-YYYY-MM-DD-<topic>.md`
- `03_KNOWLEDGE/` → `knowledge-<concept>.md`
- `02_OPERATIONS/` → `runbook-<process>.md` or `sop-<process>.md`

Collision rule:
- If a name already exists, add one short differentiator at the end
  (example: `knowledge-api-rate-limits-github.md`).

## 5) Note Templates (MVP)
Use the starter templates in `templates/` when creating new notes:
- `templates/project-note.md`
- `templates/meeting-note.md`
- `templates/knowledge-note.md`

First-time local setup + validation checklist lives in:
- `TEMPLATE_SETUP.md`

After each local template validation run, record outcome in:
- `SETUP_VALIDATION_LOG.md`

Template rules:
- Keep frontmatter minimal and useful (`type`, dates, status/owner when relevant).
- Fill only what you know now; avoid placeholder sprawl.
- Add at least one internal link before considering a note complete.

## 6) Definition of Done (for each meaningful update)
- Note is in the right folder.
- Filename follows naming conventions in this doc.
- Key context is readable by someone else later.
- At least one useful link exists.
- Changes are committed and pushed.

## 7) Weekly Hygiene Review (15 minutes)
Run this once per week to prevent note drift and stale tasks.

1. Process any unstructured notes/inbox items into the correct folders.
2. Fix notes created this week that still have no internal link.
3. Rename notes that violate naming conventions or cause ambiguous search results.
4. Archive finished items/projects that are no longer active.
5. Capture 3–5 important outcomes/lessons from the week in durable notes.
6. Commit review updates as a single small "weekly hygiene" commit.

## 8) Quick CLI Health Checks (optional, weekly)
Run these from vault root during weekly hygiene to catch drift fast.

```bash
# A) Files that violate lowercase kebab-case (ignores .obsidian/)
find . -type f -name "*.md" -not -path "./.obsidian/*" \
| grep -Ev '^\./[a-z0-9/_-]+\.md$' || true

# B) Meeting notes not following meeting-YYYY-MM-DD-<topic>.md
find 04_MEETINGS -type f -name "*.md" \
| grep -Ev '/meeting-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]+\.md$' || true

# C) Knowledge notes not following knowledge-<concept>.md
find 03_KNOWLEDGE -type f -name "*.md" \
| grep -Ev '/knowledge-[a-z0-9-]+\.md$' || true

# D) Notes with zero wikilinks (possible orphans; excludes templates/archive)
find . -type f -name "*.md" \
  -not -path "./.obsidian/*" \
  -not -path "./templates/*" \
  -not -path "./90_ARCHIVE/*" \
  -print0 | xargs -0 -I{} sh -c 'grep -q "\\[\\[" "{}" || echo "{}"'
```

Interpretation:
- No output = pass.
- Any output = rename/fix those files during hygiene review.
- For check D, treat output as review candidates (some intentional standalone notes may be valid).

## 9) Conflict-Minimizing Rules
- Pull/rebase before editing.
- Avoid editing the same note from two machines at once.
- If conflict happens:
  1. keep both versions temporarily,
  2. merge intentionally,
  3. commit with message: `resolve merge conflict in <note>`.

## 10) Change Control
- Process updates should be documented in:
  - `DECISIONS.md` (why we changed),
  - `PROGRESS.md` (what changed and when),
  - `ISSUES.md` (new risks/blockers).
