---
description: "Build and test a feature on two independent tracks: /sdd-parallel <feature>"
---

Invoke the `parallel-delivery` skill for feature: $ARGUMENTS

Check the spec and plan are approved and the plan has a Test contract. Start the `acceptance-tester` subagent for the test track (it must not read implementation source) and have it record `sdd prove red $ARGUMENTS`. Run the build track with the `build` skill without touching the acceptance tests. When all tasks are checked, run `sdd prove green $ARGUMENTS` and report both tracks.
