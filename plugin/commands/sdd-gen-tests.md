---
description: "Generate acceptance tests for a feature from its spec, in the form the project's stack runs: /sdd-gen-tests <feature>"
---

Invoke the `test-automation` skill for feature: $ARGUMENTS

Run `sdd gen-tests $ARGUMENTS`. Implement any missing steps in the project's own language (connector file for the Playwright forms, step definitions for Gherkin); never put selectors in generated tests or credentials in code. Run the command it prints against a running app and report pass, fail or gap per requirement.
