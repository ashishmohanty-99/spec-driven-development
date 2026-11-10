---
description: Profile this codebase and confirm the SDD setup
---

Invoke the `using-sdd` and `codebase-discovery` skills.

1. Run `npx specpilot scan` (or `npx specpilot init` if `.sdd/` is missing) and read the generated profile.
2. Resolve every CONFIRM item by running the detected commands. Record conventions, seams and hazards with file paths.
3. Save findings in the profile and stop for the human to confirm. Do not edit source code.
