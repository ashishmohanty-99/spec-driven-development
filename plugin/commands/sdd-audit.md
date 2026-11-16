---
description: Security self-check of the SDD setup (committed secrets, .gitignore, config, CI)
---

Run `sdd audit` and report each finding with its fix. For a FAIL about a possible credential, tell the user to remove it and rotate it; do not print the value. Do not open files listed under Protected paths.
