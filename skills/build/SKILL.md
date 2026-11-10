---
name: build
description: Implements approved tasks one at a time with test-first discipline, small commits, and requirement-tagged tests. Use when tasks.md is approved and tasks remain unchecked.
---

# Build

## Overview
Implement exactly one task at a time. Tests are the proof, and they name the requirement ids they prove so verification can be mechanical.

## Per-task loop
1. **Pick** the next unchecked task whose dependencies are done. State it and its REQ ids.
2. **Load only needed context**: the task, the relevant spec requirements, the touched files. Not the whole repo.
3. **RED.** Write a failing test that expresses the acceptance criterion. Put the requirement id in the test name or a comment tag, e.g. `it('REQ-003: rejects expired token')`. Run it; see it fail for the right reason.
4. **GREEN.** Write the least code that passes. Follow conventions recorded in the profile.
5. **Refactor** only inside the task's files, with tests green.
6. **Prove.** Run the task's Verify command plus the profile's lint/typecheck/test commands. Read the output; do not assume.
7. **Commit** one logical change with a message naming the task (`T-003: …`). Check the task box in `tasks.md`.
8. Run `npx specpilot verify <feature>`. Then pick the next task, or stop at a checkpoint.

If `.sdd/extensions/tools.md` describes internal tooling relevant to the task (scanners, generators, trackers), call it exactly as documented and report its output; never invent flags.

## When things go wrong
- Test fails unexpectedly: debug the cause; never weaken or skip the test to pass.
- The spec turns out wrong: stop, load `spec-sync`, change the spec first with a decision-log entry, get approval, then continue.
- Task is bigger than planned: stop and split it in `tasks.md`.
- You need a dependency, migration or public API change not in the plan: stop and ask.

## Autonomy modes
Default is one task then pause for review. If the human explicitly authorises a run of tasks, still verify and commit each task separately and stop on any failure or Ask-first item.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "Tests after, it's faster" | Tests written after pass by construction and prove nothing. |
| "I'll fix that unrelated bug while here" | Out-of-scope diffs make review and rollback harder. Log it. |
| "Several tasks in one commit" | Per-task commits make each step revertable and traceable. |
| "Mark it done, I'm sure it works" | Done requires command evidence. |

## Red Flags
- Tests that do not reference any REQ id
- Test edited to match broken behaviour
- Diff touching files outside the task's list
- Checked boxes with no commit

## Verification
- [ ] A failing test existed before the code
- [ ] Verify and project test commands pass (output read)
- [ ] Task checked, committed, `sdd verify` clean
