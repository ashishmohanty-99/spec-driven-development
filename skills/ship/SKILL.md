---
name: ship
description: Final readiness gate before merge or release: definition of done, documentation, rollout and rollback plan, and closing the spec loop. Use after verify passes and the human wants to merge, release or deploy.
---

# Ship

## Overview
Shipping is a human decision supported by a checklist. This skill assembles the evidence and the rollback story; it never merges or deploys on its own authority.

## Process
1. Confirm `verify` passed and `verification.md` exists. If not, go back.
2. **Definition of done**, each answered with evidence:
   - All tasks checked; `sdd verify --strict` clean
   - CI green on the branch (cite the run)
   - Docs, changelog and public API notes updated
   - Config, migrations and feature flags listed with defaults
   - Monitoring/logging for new failure modes
   - `npx specpilot regression --strict` green (unit + generated Playwright e2e + traceability gates)
   - For changes to auth, input handling or a new endpoint: `security-pentest` run, findings triaged, Security section present in `verification.md`
3. **Rollout.** Describe how it reaches users (flag, staged, direct), what to watch, and the explicit rollback trigger and steps. Irreversible changes (data migrations) need a written reversal or a justified "none".
4. **Org gates and tools.** Read `.sdd/extensions/tools.md` for how to call internal systems, and apply `.sdd/extensions/gates.md` (change tickets, security sign-off, release windows). Report each as satisfied or pending; do not fake or skip.
5. **PR description** linking the spec, plan, and verification table; list requirements delivered and any deferred ones.
6. **Close the loop.** Set spec `Status: shipped` only after the human confirms release. Open ADRs reflect final decisions.
7. **Stop.** The human merges and deploys unless they explicitly delegate it for this change.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "We can roll back by reverting" | Not after a migration or external side effect. Say what actually undoes it. |
| "Docs later" | Later means never. Update them in this change. |
| "CI will catch it" | CI runs what you wrote. Verification mapped what you meant. |

## Red Flags
- No rollback plan
- Pending org gate treated as optional
- Agent merging or deploying without explicit instruction

## Verification
- [ ] Every DoD item has evidence
- [ ] Rollback trigger and steps written
- [ ] Human decision recorded
