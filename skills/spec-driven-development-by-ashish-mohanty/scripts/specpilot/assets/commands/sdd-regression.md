---
description: Run the full regression sweep (unit tests, generated e2e suite, all gates): /sdd-regression
---

Run `sdd regression --strict`. Report each step as ok, FAIL or skip with its note, and the single next action for any failure: fix the code, regenerate tests with `/sdd-gen-tests`, or resolve gate errors with `/sdd-verify`.
