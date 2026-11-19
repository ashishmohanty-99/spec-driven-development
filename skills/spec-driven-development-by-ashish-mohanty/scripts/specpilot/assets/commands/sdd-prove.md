---
description: "Record the acceptance tests failing before the code, then passing after: /sdd-prove <red|green> <feature>"
---

Run `sdd prove $ARGUMENTS` and report the result. A red run must fail and a green run must pass with the test file unchanged since red. If the tool refuses to record, explain why in one line; do not edit the tests to change the outcome.
