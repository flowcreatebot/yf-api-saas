---
type: plan
project: obsidian-knowledge-base
status: active
owner: Alfred
created: 2026-02-24
updated: 2026-02-25
---

# Obsidian Knowledge Base — Project Plan

## Objective
Build a professional, centralized Obsidian knowledge system that both Boss and Alfred can use across different machines, with Git as source of truth.

## Success Criteria
- A private Git repo is established as canonical source.
- Standardized project documentation exists and is actively maintained:
  - PLAN.md
  - ISSUES.md
  - PROGRESS.md
  - DECISIONS.md
- Initial information architecture is in place and documented.
- Repeatable operating workflow exists for capture, processing, review, and retrieval.

## Scope
### In scope
- Vault structure design and documentation standards.
- Template and metadata standards for project notes.
- Git-first collaboration model (server + local Obsidian).
- Initial project setup and execution cadence.

### Out of scope (for now)
- Advanced plugin-heavy automation.
- Public publishing.
- Full migration of all historical notes in one pass.

## Workstreams
1. **Repository & Access Setup**
   - Create/private repo
   - Confirm local + server access model
2. **Vault IA Setup**
   - Folder taxonomy
   - Core templates
   - Naming conventions
3. **Operating Workflow**
   - Capture → Process → Review cadence
   - Rules for project docs and decision logging
4. **Execution Rhythm**
   - Hourly cron for structured incremental progress
   - Regular status updates in this channel

## Initial Information Architecture (v1)
- 00_INDEX/
- 01_PROJECTS/
- 02_OPERATIONS/
- 03_KNOWLEDGE/
- 04_MEETINGS/
- 90_ARCHIVE/

## Milestones
- M1: Project files and baseline plan created.
- M2: Git collaboration path confirmed and documented.
- M3: Obsidian vault scaffold finalized.
- M4: First practical usage loop completed (add/update/retrieve cycle).

## Open Decisions
- Keep manual Git flow only vs add Obsidian Git plugin later.
- Access-gate implementation choice for email OTP (provider/proxy details).
- Tagging strictness (lightweight vs strict taxonomy).

## Next Actions
1. Resolve Render repo access (grant Render integration access to `flowcreatebot/obsidian-kb`).
2. Configure email-OTP access gate before exposing hosted URL.
3. Convert `OPERATING_WORKFLOW.md` from draft to accepted after Boss review.
4. Run `TEMPLATE_SETUP.md` in the local vault and complete the 3-minute validation checklist for all three starter templates.
5. Apply filename conventions to initial seed notes in the live vault and fix any ambiguous wikilink targets.
