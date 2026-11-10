---
name: test-automation
description: Generates and maintains a Playwright regression suite directly from an approved spec's acceptance scenarios, keeping one test per requirement traceable by id. Use after a spec has acceptance scenarios, when tasks.md is done and the build skill needs e2e coverage, or when a spec changes and its e2e tests need to be regenerated.
---

# Test Automation

## Overview
`npx specpilot gen-tests <feature>` reads `.sdd/specs/<feature>/spec.md`, understands its
requirements and Given/When/Then acceptance scenarios, and writes a Playwright spec with one test
per scenario — each test's title carries the requirement id, so `sdd verify` and `sdd regression`
count it automatically. This closes the loop started by `specify`: the same document that defines
"done" also produces the regression test that proves it, instead of a human re-deriving tests from
a requirement by hand.

## Process
1. Confirm the spec has requirements and, ideally, acceptance scenarios (section 6). A requirement
   with no scenario still gets a test, marked `test.fixme` with a TODO naming the id — visible,
   not silently skipped.
2. Run `npx specpilot gen-tests <feature>`. It writes `tests/e2e/<feature>.spec.js` (or refreshes
   it: everything above the `SPECPILOT:GENERATED-END` marker is replaced, everything below is kept,
   so hand-added regression cases survive re-generation).
3. **Wire it to the real UI.** Generated tests call `tests/support/ui-connector.js`'s `ui()`,
   `act()` and `expect()` with the scenario's plain English. Replace the placeholders with real
   Playwright locators and assertions for this scenario. If a scenario needs to start logged in,
   implement `.sdd/extensions/ui-login.js` once (copy `.sdd/extensions/ui-login.example.js`); every
   scenario whose Given mentions "logged in" / "authenticated" calls it automatically.
4. First time in a project: `npm i -D @playwright/test && npx playwright install chromium`.
5. Run `npx playwright test`. Fix the test or the app, never both silently — if the generated test
   is wrong, fix the scenario in spec.md first (through `clarify` or `spec-sync`), then regenerate.
6. Re-run `gen-tests` whenever the spec's requirements or scenarios change. Never hand-edit the
   generated block directly; edits there are lost on the next run — add permanent extra cases below
   the marker instead.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "I'll write the Playwright test from scratch, it's just as fast" | Then it won't carry the REQ id, and `verify`/`regression` won't see it as proof. |
| "The fixme placeholders are good enough" | They mark coverage gaps on purpose; replace them before `ship`. |
| "Edit the generated block, I'll remember not to regenerate" | The next person won't. Put permanent edits below the marker. |

## Red Flags
- A committed `.spec.js` still full of `test.fixme`
- Login credentials hardcoded in `ui-connector.js` instead of read from env in `ui-login.js`
- Scenario text in spec.md that no longer matches the generated test (spec changed, generator not re-run)

## Verification
- [ ] `npx specpilot gen-tests <feature>` ran after the spec's scenarios were last edited
- [ ] No `test.fixme` remains for a requirement that is marked done in `tasks.md`
- [ ] `npx playwright test` passes against a running instance of the app
