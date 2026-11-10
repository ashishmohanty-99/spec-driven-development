---
description: Generate or refresh the Playwright regression suite for a feature from its spec: /sdd-gen-tests <feature>
---

Invoke the `test-automation` skill for feature: $ARGUMENTS

Run `npx specpilot gen-tests $ARGUMENTS`, then wire the generated tests to the real UI in `tests/support/ui-connector.js` (and `.sdd/extensions/ui-login.js` for authenticated scenarios). Do not hand-edit the generated block; add permanent extra cases below the `SPECPILOT:GENERATED-END` marker. Run `npx playwright test` and report pass/fail per requirement.
