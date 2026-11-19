---
description: "Run the security gate: secrets in the repo and its history, code scan, dependency audit"
---

Invoke the `security-gate` skill.

Run `sdd security` and report each layer as clean, findings, error or NOT RUN, naming the engine used for secrets. For a real secret, tell the person to revoke it first. Never accept a finding without looking at it, never install tools without asking, and never call a NOT RUN layer clean.
