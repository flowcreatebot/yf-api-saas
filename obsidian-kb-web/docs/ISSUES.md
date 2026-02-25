---
type: issues
project: obsidian-knowledge-base
status: active
owner: Alfred
created: 2026-02-24
updated: 2026-02-25
---

# Obsidian Knowledge Base — Issues & Risks

## Open Issues

### OB-001 — Repo not yet provisioned
- **Status:** Open
- **Impact:** Cannot establish shared source-of-truth workflow yet.
- **Needs:** Boss confirms Git provider and repo creation preference.

### OB-002 — Local accessibility gap
- **Status:** Open
- **Impact:** Boss cannot easily use server-local vault directly.
- **Mitigation:** Use Git-first model with local Obsidian vault clone.

### OB-003 — Workflow preferences still undefined
- **Status:** Open
- **Impact:** Risk of overengineering or mismatched process.
- **Needs:** Boss chooses lightweight vs structured workflow defaults.

### OB-004 — Sync strategy undecided
- **Status:** Open
- **Impact:** Potential confusion between Obsidian Sync and Git-based sync.
- **Mitigation:** Default to Git as canonical sync; Obsidian Sync optional personal-device convenience.

### OB-005 — Merge conflict risk across machines
- **Status:** Open
- **Impact:** Concurrent edits can create friction and accidental overwrites.
- **Mitigation:** Added `OPERATING_WORKFLOW.md` with conflict-minimizing git cadence and conflict resolution steps.

### OB-006 — Template setup not yet enabled in local Obsidian
- **Status:** Open
- **Impact:** New template files may remain unused, causing continued note-format inconsistency.
- **Mitigation:** Follow `TEMPLATE_SETUP.md` to configure Templates/Templater path to `templates/` and run the 3-minute validation checklist.

### OB-007 — Accidental cross-project commits from workspace root
- **Status:** Open
- **Impact:** Unrelated files from other projects can be committed together, creating noisy history and rollback risk.
- **Mitigation:** Updated `OPERATING_WORKFLOW.md` to use path-scoped staging (`git add projects/obsidian-knowledge-base`) plus `git status --short` before commit.

### OB-008 — Knowledge-base drift without scheduled maintenance
- **Status:** Open
- **Impact:** Unlinked notes, stale project pages, and backlog clutter can reduce retrieval quality over time.
- **Mitigation:** Added a 15-minute weekly hygiene review checklist to `OPERATING_WORKFLOW.md` and set expectation for a dedicated small maintenance commit.

### OB-009 — Inconsistent filenames reduce link/search reliability
- **Status:** Open
- **Impact:** Similar notes with inconsistent naming can produce ambiguous wikilink autocomplete results and slower retrieval.
- **Mitigation:** Added explicit filename conventions and weekly rename check in `OPERATING_WORKFLOW.md`; enforce naming in Definition of Done.

## Risks
- **R1:** Documentation drift if updates happen in chat but not files.
  - *Control:* Every session updates PROGRESS.md and/or ISSUES.md.
- **R2:** Inconsistent note format.
  - *Control:* Standard frontmatter + templates.
- **R3:** Too much complexity too early.
  - *Control:* MVP-first rollout, defer advanced automations.

### OB-010 — Render cannot fetch new private GitHub repo yet
- **Status:** Open
- **Impact:** `obsidian-kb-web` service creation fails because Render currently cannot access `https://github.com/flowcreatebot/obsidian-kb`.
- **Mitigation:** Grant Render GitHub app/repo access to `flowcreatebot/obsidian-kb`, then re-run service creation.

### OB-011 — Email OTP gate not configured yet for hosted vault
- **Status:** Open
- **Impact:** Deploying directly on Render would expose docs publicly before access control is in place.
- **Mitigation:** Add access-proxy layer with email OTP before sharing production URL.

## Blockers
- B1: OB-010 must be resolved before Render can auto-deploy from private GitHub repo.
- B2: OB-011 must be resolved before hosted URL can be shared for production use.
