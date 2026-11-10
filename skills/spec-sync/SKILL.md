---
name: spec-sync
description: Detects and resolves drift between specs and code so the spec stays the source of truth, including reverse-documenting behaviour for legacy code with no spec. Use when implementation diverges from the spec, requirements change mid-build, or an existing feature needs a baseline spec.
---

# Spec Sync

## Overview
A stale spec is worse than none: it is trusted and wrong. Direction of change is always decided explicitly: either the code is wrong, or the spec is.

## Drift workflow (spec exists)
1. Identify the divergence precisely: requirement id, what the spec says, what the code does, evidence (path, test).
2. Decide with the human which side is right.
   - **Code wrong:** add or fix a task; do not edit the spec.
   - **Spec wrong or outdated:** edit the requirement in place (keep the id), add a decision-log row, set `Status: draft`, and re-run clarify and approval. Downstream plan/tasks affected must be updated.
   - **New behaviour not specified:** add a new `REQ-` id; never retrofit by stretching an old one.
3. Run `npx specpilot verify <feature>`. Update tests to match the decision.

## Baseline workflow (legacy code, no spec)
1. Pick one capability. Read its code and tests.
2. Write requirements describing **observed** behaviour in EARS form, each with a cited path. Tag assumptions `[NEEDS CLARIFICATION]` where intent is unknowable from code.
3. Mark the spec `Status: draft` and label it "baseline (observed)". A human confirms intended behaviour before it governs changes.
4. Add characterization tests for requirements lacking any, naming the ids.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "Just update the spec to match" | Silently blessing a bug is how specs lose meaning. Decide which is wrong. |
| "Baseline specs are too slow" | Do one capability at a time, only where you are about to change code. |

## Red Flags
- Spec edited with no decision-log entry
- Renumbered requirement ids
- Baseline spec presented as intended design

## Verification
- [ ] Each drift item resolved in a named direction
- [ ] Decision log updated; approval re-requested if spec changed
- [ ] `sdd verify` clean
