# SpecPilot User Guide

This guide takes you from install to shipping your first feature. Each step says **who acts**
(you or the agent), **what is produced**, and **what you check before approving**.

## 0. Concepts in one minute
- **Gate:** a point where the agent must stop and a human approves. The agent saves its artifact and
  ends its turn; you approve in your next message (and set the `Status:` line yourself).
- **Artifacts** live in `.sdd/specs/<feature>/`: `spec.md` → `plan.md` → `tasks.md` → `verification.md`.
- **IDs are permanent:** requirements `REQ-001`, tasks `T-001`. Tests mention the REQ ids they prove.
  That chain is what `sdd verify` checks.
- **Constitution:** a short list of checkable rules for the whole repo (`.sdd/constitution.md`).

## 1. Install
```bash
npx specpilot init          # or: --agent generic for non-Claude agents
npx specpilot doctor              # confirms the install
```
The CLI is also available as `sdd` once installed (`npm i -D specpilot`). Below, `npx specpilot` is used throughout.

## 2. Teach it your codebase (once)
**You:** `/sdd-init`
**Agent:** runs `sdd scan`, executes the detected build/test/lint commands, reads sample modules, and
records conventions, seams (where features attach), and hazards in `.sdd/codebase-profile.md`.
**You check:** commands are correct; conventions match how your team really works; protected paths
list is complete. Edit the section "Human-supplied context": it is preserved on every re-scan.

**You:** `/sdd-constitution`
**Agent:** drafts `.sdd/constitution.md`, each rule tied to an enforcing tool or marked `(review)`.
**You:** edit, then change `Status: draft` to `Status: ratified`.

## 3. Specify a feature
**You:** `/sdd-spec "Throttle failed logins: lock for 15 min after 5 failures"`
**Agent:** creates `.sdd/specs/login-throttle/spec.md`, grounded in your code, with:
- Requirements in EARS form with stable ids, e.g.
  `REQ-001: When a user fails login 5 times within 10 minutes, the auth service shall reject further attempts for 15 minutes.`
- Non-goals, boundaries (Always / Ask first / Never), and `[NEEDS CLARIFICATION: …]` for unknowns.
**You check:** Can each requirement be tested? Is anything missing (error cases, who is affected)?
If the idea is large, the agent first proposes a capability map (modules + build order) to approve.

## 4. Clarify
**You:** `/sdd-clarify login-throttle`
**Agent:** answers what the code can answer, asks you at most five ranked questions with a
recommendation each, logs decisions, removes the markers.
**You:** when satisfied, edit `spec.md`: `Status: draft` → `Status: approved`.
```bash
npx specpilot verify login-throttle      # must show no errors before planning
```

## 5. Plan
**You:** `/sdd-plan login-throttle`
**Agent:** explores read-only, writes `plan.md`: approach vs rejected alternative, exact files to touch,
interfaces, a table mapping **every REQ** to where it is satisfied and how it is tested, risks and rollback.
**You check:** the approach fits your architecture; "Ask first" items (new dependency, migration,
public API change) are ones you accept. Approve in chat.

## 6. Tasks
**You:** `/sdd-tasks login-throttle`
**Agent:** writes `tasks.md`, vertical slices such as
`- [ ] T-001 Count failed attempts per account (covers: REQ-001)` each with Acceptance, Verify, Files.
It runs `sdd verify` to prove every REQ is covered. **You** approve.

## 7. Build
**You:** `/sdd-build login-throttle` (repeat per task)
**Agent:** one task: failing test named `REQ-001: …` → minimal code → project checks → commit
(`T-001: …`) → tick the box → `sdd verify`. It stops after each task unless you explicitly say to run several.
**You check:** the diff stays inside the task's files; tests assert the requirement, not the implementation.

## 8. Verify
**You:** `/sdd-verify login-throttle`
**Agent:** `sdd verify --strict`, full test/lint/typecheck, `verification.md` (REQ → test evidence),
an independent `spec-reviewer` pass on correctness, readability, architecture, security, performance.
**You:** decide on findings.

## 9. Ship
**You:** `/sdd-ship login-throttle`
**Agent:** definition-of-done evidence, rollout and rollback plan, your org's extra gates, PR text.
**You:** merge and deploy. The agent will not.

## Day-to-day commands
| Command | Use |
|---|---|
| `npx specpilot status` | phase and progress of every feature |
| `npx specpilot verify [feature] [--strict]` | gate check; exit code 1 on errors (use in CI) |
| `npx specpilot new <name>` | create a spec skeleton |
| `npx specpilot scan` | refresh the codebase profile |
| `npx specpilot doctor` | installation health |
| `/sdd-sync <feature>` | reconcile spec and code when they drift |
| `/sdd-status` | agent summary with the single next action |

## When to skip SDD
One-line fixes, typos, and bugs with an obvious cause. Fix, add a regression test, move on. If
the "small" change grows past about 30 minutes or touches several modules, write a short spec.

## Existing code with no spec
Use `/sdd-sync` in baseline mode on one capability at a time, only where you are about to change
behaviour. It writes observed-behaviour requirements and characterization tests for you to confirm.

## Run the gates in CI
```yaml
- run: npx specpilot verify --strict
```
Fails the build on uncovered requirements, orphan tasks, placeholders, open questions, or built
requirements without a REQ-named test.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `plan/tasks exist but spec.md is not "Status: approved"` | A human must set the status line; agents must not. |
| `REQ-00X is not covered by any task` | Add `covers: REQ-00X` to a task or add a task. |
| `has completed task(s) but no test file mentions it` | Put the id in the test name or a comment. |
| Requirement not detected | Definitions need the colon form `- REQ-001: …`; scenarios use `REQ-001 —`. |
| Agent ignores the process | Confirm `CLAUDE.md`/`AGENTS.md` has the SpecPilot block and `npx specpilot doctor` passes. |
| Profile commands wrong | Fix them under "Human-supplied context"; re-scan keeps your edits. |

## Upgrading
`npx specpilot init --force` refreshes skills and commands to the latest version. It overwrites
files under `.claude/skills`, `.claude/commands` and `.sdd/templates`, so keep customisations in
`.sdd/extensions/` (see [EXTENDING.md](EXTENDING.md)).
