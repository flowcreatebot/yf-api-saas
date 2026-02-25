---
type: decisions
project: obsidian-knowledge-base
status: active
owner: Alfred
created: 2026-02-24
updated: 2026-02-25
---

# Obsidian Knowledge Base — Decision Log

## DEC-001 — Use Git as canonical source of truth
- **Date:** 2026-02-24
- **Status:** Accepted
- **Context:** Alfred runs on a different server; direct server-local vault usage is inconvenient for Boss.
- **Decision:** Use a private Git repo as canonical data layer; both local Obsidian and server workflow sync through git.
- **Consequences:**
  - + Cross-machine collaboration becomes reliable and auditable.
  - + History/versioning included by default.
  - - Requires lightweight git discipline (pull/push cadence).

## DEC-002 — Use standardized project docs for execution
- **Date:** 2026-02-24
- **Status:** Accepted
- **Decision:** Use PLAN.md, ISSUES.md, PROGRESS.md, and DECISIONS.md per active project.
- **Consequences:**
  - + Clarity and continuity improve.
  - + Easier handoff between chat and files.

## DEC-003 — Default to manual Git sync cadence (MVP)
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Sync tooling choice (Obsidian Git plugin vs manual flow) is still open, but work needs a safe default now.
- **Decision:** Use manual git CLI cadence as default (`pull --rebase` at start, small commits, push at end) until plugin-based sync is explicitly chosen.
- **Consequences:**
  - + Immediate, tool-agnostic workflow that works on any machine.
  - + Lower setup complexity during early phase.
  - - Requires disciplined habit from both collaborators.

## DEC-004 — Adopt a minimal starter template set for core note types
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Capture speed is good, but inconsistent note shape will reduce retrieval quality and handoff clarity.
- **Decision:** Add and use three lightweight templates in `templates/` for Project, Meeting, and Knowledge notes, with minimal frontmatter and explicit links/action sections.
- **Consequences:**
  - + Faster note creation with consistent structure.
  - + Better downstream retrieval and review quality.
  - - Small upfront effort to wire templates into local Obsidian template workflow.

## DEC-005 — Use path-scoped staging for project commits
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** This workspace often has multiple active projects, so `git add -A` from repo root can accidentally include unrelated changes.
- **Decision:** Default end-of-session staging to `git add projects/obsidian-knowledge-base` for this project.
- **Consequences:**
  - + Reduces accidental cross-project commits.
  - + Keeps commit history cleaner and easier to review.
  - - Requires remembering project path when committing from workspace root.

## DEC-006 — Keep a lightweight per-machine template validation log
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Template setup can differ per machine/vault; without a persistent record we may repeat setup checks or miss environment-specific breakage.
- **Decision:** Add `SETUP_VALIDATION_LOG.md` and require logging each template validation run in one compact line.
- **Consequences:**
  - + Faster troubleshooting when template insertion fails on a specific machine.
  - + Clear visibility of what has already been validated.
  - - Small ongoing discipline cost to append a line after each run.

## DEC-007 — Add a weekly hygiene review cadence
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Daily capture and commit flow exists, but without a recurring cleanup pass the vault can accumulate unlinked notes, stale tasks, and outdated active-project pages.
- **Decision:** Add a 15-minute weekly hygiene review checklist to `OPERATING_WORKFLOW.md` as a standard maintenance step.
- **Consequences:**
  - + Reduces knowledge-base drift and keeps retrieval quality high.
  - + Encourages consistent archiving and consolidation of weekly learnings.
  - - Adds a small recurring maintenance commitment.

## DEC-008 — Adopt lightweight filename conventions per note type
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Template structure is now standardized, but inconsistent filenames still reduce search clarity and create ambiguous wikilink suggestions.
- **Decision:** Add explicit MVP naming rules in `OPERATING_WORKFLOW.md` (kebab-case + per-folder patterns for project/meeting/knowledge/operations notes) and make filename compliance part of Definition of Done.
- **Consequences:**
  - + Cleaner search/autocomplete behavior and fewer duplicate-looking notes.
  - + Easier review and maintenance during weekly hygiene.
  - - Requires occasional renaming of legacy notes to fit conventions.

## DEC-009 — Add lightweight CLI naming audits to weekly hygiene
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Naming conventions are defined, but manual spot-checking is easy to skip and can miss drift as note volume grows.
- **Decision:** Add three copy/paste CLI checks in `OPERATING_WORKFLOW.md` (global kebab-case, meeting pattern, knowledge pattern) as an optional weekly hygiene accelerator.
- **Consequences:**
  - + Faster detection of naming drift with low effort.
  - + Keeps conventions enforceable without introducing plugin/tooling overhead.
  - - Uses regex-based checks, so occasional false positives may need manual judgment.

## DEC-010 — Add a lightweight orphan-note audit to weekly hygiene
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Naming checks now catch file-pattern drift, but they do not reveal notes that have no incoming/outgoing connective structure, which can hurt later retrieval.
- **Decision:** Add an optional CLI check in `OPERATING_WORKFLOW.md` to list markdown files with zero `[[wikilinks]]` (excluding templates/archive) as review candidates during weekly hygiene.
- **Consequences:**
  - + Surfaces potentially isolated notes early, before they become forgotten knowledge.
  - + Keeps linking quality visible without requiring additional plugins.
  - - Generates review candidates, not strict violations; some standalone notes may be intentionally unlinked.

## DEC-011 — Host a remote web mirror (Render) so Boss can view full vault without local Obsidian
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Boss wants full-vault visibility without running Obsidian locally; Alfred runs on a separate server.
- **Decision:** Maintain a private GitHub repo (`flowcreatebot/obsidian-kb`) as canonical for hosted mirror deployment and target Render for always-online viewing.
- **Consequences:**
  - + Boss can access docs from anywhere via browser.
  - + Deployment can auto-update on commits.
  - - Requires hosting auth layer to avoid exposing internal docs publicly.

## DEC-012 — Use email OTP access control for hosted vault access
- **Date:** 2026-02-25
- **Status:** Accepted
- **Context:** Boss confirmed preference for password-protected access with email OTP (`daniel@flowcreate.solutions`).
- **Decision:** Gate hosted vault access with email OTP (via access proxy layer), rather than leaving Render endpoint public.
- **Consequences:**
  - + Secure browser access without local app setup.
  - + No shared static password required.
  - - Needs one-time identity/access-provider configuration before go-live.
