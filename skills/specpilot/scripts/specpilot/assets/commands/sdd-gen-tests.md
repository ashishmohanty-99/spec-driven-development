---
description: Generate the pytest-playwright regression tests for a feature from its spec: /sdd-gen-tests <feature>
---

Invoke the `test-automation` skill for feature: $ARGUMENTS

Run `sdd gen-tests $ARGUMENTS`. For any phrase without a matching step, add a `@step` to `tests/e2e/ui_connector.py` (never selectors in the generated test, never credentials in code). Run `pytest tests/e2e` against a running app and report pass, fail or gap per requirement.
