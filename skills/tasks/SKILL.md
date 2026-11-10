---
name: tasks
description: Breaks an approved plan into small ordered vertical-slice tasks, each covering named requirement ids with acceptance criteria and a verification command. Use when plan.md is approved and tasks.md does not exist.
---

# Tasks

## Overview
Tasks turn the plan into units an agent can finish and prove one at a time. Traceability is built in: every task names the requirements it covers.

## Process
1. Confirm `plan.md` is approved. Read spec and plan.
2. **Slice vertically.** Each task delivers a thin end-to-end behaviour (route + logic + storage + test), not a horizontal layer ("all models first"). Each leaves build and tests green.
3. **Size.** One focused session, at most about five files. If larger, split. If trivial and coupled, merge.
4. **Order by dependency**, then risk: do the riskiest unknown early. Mark which tasks could run in parallel.
5. **Write in the required format** into `tasks.md`:
   `- [ ] T-001 Imperative title (covers: REQ-001, REQ-003)` followed by Acceptance, Verify, Files, Depends on.
6. Add a checkpoint after every two or three tasks (full test run and human glance).
7. Include a first task for missing test infrastructure if the profile shows none.
8. Run `npx specpilot verify <feature>`: every REQ covered, no orphan tasks, no unknown ids. **Stop** for approval.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "Tasks are busywork, just build it" | They are the checkpoints that make agent output reviewable. |
| "Group the DB work first" | Horizontal slices defer integration risk to the end. |
| "Requirement coverage is implied" | Unmapped requirements are the ones that never get tested. |

## Red Flags
- Task titles like "implement backend"
- A task touching more than about five files
- `verify` reports uncovered requirements
- No verify step on a task

## Verification
- [ ] `npx specpilot verify <feature>` has no coverage errors
- [ ] Every task has acceptance and a runnable verify step
- [ ] Human approved the list
