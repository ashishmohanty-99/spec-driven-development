---
name: plan
description: Produces a technical plan from an approved spec by mapping each requirement to concrete code touch points, interfaces, risks and a verification strategy. Use when spec.md is Status approved and no plan.md exists.
---

# Plan

## Overview
The plan says how the approved spec will be satisfied inside this codebase. It is reviewable: a human should be able to say "yes, that approach" or "change X" without reading code.

## Preconditions
`spec.md` is `Status: approved` and `npx specpilot verify <feature>` has no errors. Otherwise stop and route back to specify or clarify.

## Process
1. **Read read-only.**  Open every file you expect to change and its tests. Use the profile's seams. Do not edit anything.
2. **Choose the approach.** Compare at least two options against the constitution (layering, dependencies, migrations). Prefer the smallest change that fits existing patterns. A new dependency, schema migration or public API change is an "Ask first" item: flag it prominently.
3. **Fill `plan.md`** from the template (`.sdd/templates/plan.md`):
   - Touch points table with real paths and the requirement each serves
   - Interfaces and data shapes as signatures or schemas
   - **Requirement → design map**: every `REQ-` id appears with where and how it is proven
   - Risks with a rollback path for anything irreversible
   - Constitution check, citing rules by section
3a. **Org rules.** If `.sdd/extensions/rules.md` exists, check the plan against it and cite each rule in the constitution check.
4. **Record significant decisions** as ADRs in `.sdd/adr/` using `.sdd/templates/adr.md`.
5. **Verification strategy.** Name the exact commands from the profile that prove the feature.
6. Run `npx specpilot verify <feature>`. Save. **Stop** for human approval.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "I'll figure out files while coding" | Surprises in touch points are the top cause of oversized diffs. |
| "One approach is obviously right" | Writing the rejected alternative proves it. |
| "A new library will be quicker" | Dependencies are team decisions. Ask first. |

## Red Flags
- Touch points that are directories rather than files
- A requirement missing from the design map
- No rollback path for a migration
- Plan includes work no requirement asks for

## Verification
- [ ] Every REQ appears in the design map
- [ ] Ask-first items are called out
- [ ] Constitution check completed
- [ ] Human approved before tasks begin
