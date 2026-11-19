---
name: parallel-delivery
description: "Runs the build and the acceptance tests as two independent tracks from the same approved spec, then proves the tests failed before the code existed and pass after it, unchanged. Use when a spec and plan are approved and the team wants to ship faster without weakening verification, when acceptance tests should be written by someone who has not seen the implementation, or when asked to work in parallel."
---

# Parallel Delivery

## Overview
Once a spec is clear, nothing about the tests depends on the code. So two tracks can start from the same approved documents and run at the same time:

```
                      ┌── BUILD TRACK ── tasks ── code, one task at a time ──┐
approved spec + plan ─┤                                                      ├─ same tests go green ── verify
                      └── TEST TRACK ─── acceptance tests ── recorded RED ───┘
```

The speed comes from parallelism. The trust comes from independence: the tests are written by an agent that never sees the implementation, so they check what was asked rather than what was built. `sdd prove` records that the tests failed first and passed later without being edited.

## Preconditions
- The spec says `Status: approved` and has a Given/When/Then scenario for each requirement.
- The plan is approved and has a **Test contract** section: routes, field labels, test ids, API shapes. Both tracks build to that contract; neither may change it alone.

## Process
1. **Start the test track with a separate agent.** Launch the `acceptance-tester` subagent (or a second session) with the feature name. Give it only the spec, the plan's Test contract and the acceptance-test folder. It must not read the implementation source.
2. **Test track:** `sdd gen-tests <feature>`, implement any missing steps from the contract, then record the failing run:
   `sdd prove red <feature>`. The run must fail. If it passes, the tests prove nothing new; stop and find out why.
3. **Build track, at the same time:** follow the `tasks` and `build` skills as usual. The builder never edits the feature's acceptance-test file or the recorded evidence.
4. **Join.** When every task is checked, run `sdd prove green <feature>`. The same test file, byte for byte, must now pass.
5. **If the tests have to change** (the spec was wrong, or the contract moved): go through `spec-sync`, change the spec or contract with the person's approval, regenerate, and record a new red run. Never edit a test to make it pass.
6. **Finish** with `sdd regression --strict`, then `verify`. The feature's tests are already in the acceptance-test folder, so they are part of the regression suite from now on with no extra step.

## Roles
| Role | May read | May write | Must not |
|---|---|---|---|
| Tester | spec, plan's Test contract, acceptance-test folder | acceptance tests and steps | read or edit implementation source |
| Builder | everything | source, unit tests, tasks.md | edit the feature's acceptance tests or `evidence.json` |
| Person | everything | approvals | be skipped |

## What stays with a person
Spec approval, plan approval, the task list and the merge. Parallelism removes waiting between those points; it does not remove them.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "One agent can write both, it's simpler" | Then the tests describe the code, not the requirement. Independence is the point. |
| "Skip the red run, the tests obviously fail" | Tests that pass against nothing are common. One command proves it. |
| "The test is wrong, I'll fix it so it passes" | Changing a test after red voids the proof. Change the spec first, then record red again. |
| "The contract is in my head" | Two tracks with an unwritten contract meet in the middle and miss. |

## Red Flags
- The builder's diff touches the feature's acceptance-test file
- A green run recorded with no red run before it
- The tester asking to see the implementation "to get the selectors"
- Tests and code landing in one commit by one author

## Verification
- [ ] Red was recorded before the first build task was finished
- [ ] Green was recorded with an unchanged test file (`sdd verify` reports no red-first problem)
- [ ] The Test contract in plan.md matches what both tracks used
- [ ] `sdd regression --strict` passes
