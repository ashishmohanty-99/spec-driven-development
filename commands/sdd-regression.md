---
description: Run the full regression sweep (unit tests, generated Playwright e2e, traceability gates): /sdd-regression [--strict]
---

Run `npx specpilot regression --strict` (add `--pentest <target>` if a security scan should run in the same sweep). Report each step's result (unit tests, e2e suite, gate check, pentest) and, for any failure, the next action: fix the code, regenerate tests with `/sdd-gen-tests`, or resolve gate errors with `/sdd-verify`.
