# Central Command Dashboard Plan (Discord)

## Purpose
Single place to track progress across all projects, starting with `yf-api-saas`.

## Proposed Discord structure
- `#central-command` (high-level updates only)
- `#project-yf-api-saas` (engineering updates)
- `#alerts-build-and-tests` (test failures + deploy alerts)
- `#blocked-needs-boss` (only unblock requests)

## Update policy
- Keep updates short (2-6 lines).
- Only send when:
  - milestone completed
  - blocker needs decision/input
  - risky decision approval required
- For routine no-change heartbeats: no noisy message.

## YF API status card template
- Build/Test: ✅/❌
- Billing/Auth: ✅/⚠️/❌
- API Coverage: % endpoints covered by tests
- Last meaningful change: short sentence
- Next action: one line

## Rollout phases
1. Wire message routing to Discord project channel IDs.
2. Post automated daily test summary at 09:30 Asia/Bangkok.
3. Add heartbeat milestone updates to `#project-yf-api-saas`.
4. Add weekly executive summary to `#central-command`.
