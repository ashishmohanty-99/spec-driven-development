---
name: verify
description: Proves a built feature meets its spec through traceability checks, a full test run, requirement-by-requirement evidence and a five-axis code review. Use when all tasks are checked, before ship, or when asked whether a feature is really done.
---

# Verify

## Overview
Verification answers one question: does the code satisfy every approved requirement, with evidence? It combines mechanical checks (the CLI) with judgement (review).

## Process
1. **Mechanical gate.** `sdd verify <feature> --strict`. Every ERROR must be fixed: uncovered requirements, orphan tasks, requirements with completed tasks but no test naming them, leftover clarification markers.
2. **Regression sweep.** `sdd regression --strict` runs the project's own tests, the generated pytest-playwright suite (`test-automation`), and the traceability gates in one pass. If no e2e suite exists yet for user-facing requirements, run `test-automation` first.
3. **Full project checks.** Run the profile's build, lint, typecheck and test commands. Record results.
4. **Evidence table.** For each requirement, record the test (path::name) and what it asserts. Put it in `.sdd/specs/<feature>/verification.md`:
   | REQ | Test | Result | Notes |
5. **Behavioural check.** For user-facing behaviour, exercise it (CLI run, request, browser). A passing unit test does not replace seeing it work.
6. **Five-axis review** of the diff against the base branch (use the `spec-reviewer` subagent for an independent read):
   - **Correctness** vs spec, edge cases, error paths
   - **Readability** and consistency with profile conventions
   - **Architecture** vs constitution invariants
   - **Security**: input handling, authz, secrets, dependency changes
   - **Performance**: obvious hot paths, N+1, unbounded work
   - **Security**, deeper than the checklist above: if the change touches auth, input handling or a new endpoint, run `security-pentest`.
7. **Scope audit.** Diff contains nothing unrelated to listed tasks.
8. **Secrets.** `sdd audit` passes: no credential in specs, tests or agent files.
9. Extension gates: read `.sdd/extensions/gates.md` and satisfy or report each.
10. Report: pass/fail per requirement, defects found, residual risk. **Stop** for human sign-off.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "Tests are green, so it's verified" | Green tests only prove what they assert. Map them to requirements. |
| "Review is for humans" | An independent agent pass catches different issues cheaply. |
| "Strict mode is too strict" | Warnings tolerated now become unverified requirements later. |

## Red Flags
- A requirement with no named test
- "Verified" with no commands shown
- Unexplained skipped or deleted tests

## Verification
- [ ] `sdd verify --strict` exits 0
- [ ] `verification.md` maps every REQ to evidence
- [ ] Review findings fixed or accepted explicitly by the human
