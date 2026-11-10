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

## 8. Generate the regression suite
**You:** `/sdd-gen-tests login-throttle`
**Agent:** reads the spec's acceptance scenarios and writes `tests/e2e/login-throttle.spec.js`, one
Playwright test per requirement, named `REQ-001: …` so it counts as that requirement's test.
**You:** once per project, fill in `tests/support/ui-connector.js` with real selectors (and
`.sdd/extensions/ui-login.js` if scenarios need to start logged in) — see "UI connectors" below.

## 9. Verify
**You:** `/sdd-verify login-throttle`
**Agent:** `npx specpilot regression --strict` (unit tests + the Playwright suite + traceability
gates), `verification.md` (REQ → test evidence), an independent `spec-reviewer` pass on
correctness, readability, architecture, security, performance. For changes to auth, input handling
or a new endpoint, also runs `/sdd-pentest` (see "Penetration testing" below).
**You:** decide on findings.

## 10. Ship
**You:** `/sdd-ship login-throttle`
**Agent:** definition-of-done evidence, rollout and rollback plan, your org's extra gates, PR text.
**You:** merge and deploy. The agent will not.

## UI connectors
Generated Playwright tests never guess at your markup. They call three functions in
`tests/support/ui-connector.js` — `ui(page, given)`, `act(page, when)`, `expect(page, then)` — with
the plain-English scenario text, so you can see exactly which line of the spec you're implementing
a selector for. First time in a project:
```bash
npm i -D @playwright/test
npx playwright install chromium
```
Then edit `ui-connector.js`'s `act`/`expect` for each scenario. If a scenario's Given mentions
"logged in" or "authenticated", copy `.sdd/extensions/ui-login.example.js` to
`.sdd/extensions/ui-login.js` and implement `login(page, baseURL)` once — every such scenario calls
it automatically. Read credentials from env vars (`SDD_UI_USER`, `SDD_UI_PASS` or your own names);
never commit them. Set `SDD_BASE_URL` to point tests at a local, staging, or preview environment.

## Penetration testing
`npx specpilot pentest --target <path|url>` wraps the open-source
[Strix](https://github.com/usestrix/strix) AI pentesting agent — SpecPilot does not bundle its code,
only invokes its CLI consistently. One-time setup:
```bash
curl -sSL https://strix.ai/install | bash
export STRIX_LLM="openrouter/z-ai/glm-5.3"   # or another supported provider, see docs.strix.ai
export LLM_API_KEY="..."
```
Docker must be running. Then:
```bash
npx specpilot pentest --target ./app --fail-on high            # source
npx specpilot pentest --target https://staging.example.com --fail-on high   # deployed app
```
**Only scan systems you own or have explicit written permission to test.** Without Strix installed
or without credentials, the command prints how to fix that and exits 0 — a **skip**, not a pass;
`ship` must not treat a skipped scan as evidence.

## Day-to-day commands
| Command | Use |
|---|---|
| `npx specpilot status` | phase and progress of every feature |
| `npx specpilot verify [feature] [--strict]` | gate check; exit code 1 on errors (use in CI) |
| `npx specpilot gen-tests <feature>` | generate/refresh the Playwright suite from the spec |
| `npx specpilot regression [--strict] [--pentest <target>]` | unit + e2e + gates (+ optional pentest), one exit code |
| `npx specpilot pentest --target <path\|url>` | Strix security scan |
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
- run: npx specpilot regression --strict
```
Runs the project's own test script, the generated Playwright suite (if `playwright.config.js` is
present), and `sdd verify --strict` for every feature, failing the build on uncovered requirements,
orphan tasks, placeholders, open questions, or built requirements without a REQ-named test. Add
`--pentest <target>` to include a Strix scan in the same check once credentials are configured as
CI secrets (see [Strix's CI/CD docs](https://docs.strix.ai/integrations/ci-cd) for provider-specific
snippets). Prefer `npx specpilot verify --strict` alone only where no e2e suite or pentest is set up yet.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `plan/tasks exist but spec.md is not "Status: approved"` | A human must set the status line; agents must not. |
| `REQ-00X is not covered by any task` | Add `covers: REQ-00X` to a task or add a task. |
| `has completed task(s) but no test file mentions it` | Put the id in the test name or a comment. |
| Requirement not detected | Definitions need the colon form `- REQ-001: …`; scenarios use `REQ-001 —`. |
| Agent ignores the process | Confirm `CLAUDE.md`/`AGENTS.md` has the SpecPilot block and `npx specpilot doctor` passes. |
| Profile commands wrong | Fix them under "Human-supplied context"; re-scan keeps your edits. |
| `Cannot find module '@playwright/test'` | Run `npm i -D @playwright/test && npx playwright install chromium` in the project (not in SpecPilot itself). |
| "Strix is not installed" / STRIX_LLM missing | Expected until you set it up — see "Penetration testing". The run is a skip, not a failure to work around. |
| Generated test still has `test.fixme` | Add a Given/When/Then acceptance scenario for that REQ in spec.md, then re-run `sdd gen-tests`. |

## Upgrading
`npx specpilot init --force` refreshes skills and commands to the latest version. It overwrites
files under `.claude/skills`, `.claude/commands` and `.sdd/templates`, so keep customisations in
`.sdd/extensions/` (see [EXTENDING.md](EXTENDING.md)).
