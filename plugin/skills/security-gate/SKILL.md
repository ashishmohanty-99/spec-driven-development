---
name: security-gate
description: "Runs and interprets the layered security gate - secret scanning of the whole repository and its git history, static code analysis, dependency audit and penetration test - and triages what it finds. Use before verify or ship, when asked whether the code is secure or has vulnerabilities, when a secret may have been committed, or when a security scan reports NOT RUN."
---

# Security Gate

## Overview
One command checks four different things. They answer different questions, and none replaces another:

| Layer | Question | Engine |
|---|---|---|
| Secrets | Is a key or password in the repository or its history? | TruffleHog or gitleaks if installed, otherwise the built-in scanner |
| Code scan | Does the source contain exploitable patterns? | The analyser for the stack (semgrep, bandit, gosec, brakeman) |
| Dependencies | Do third-party packages have known vulnerabilities? | osv-scanner, trivy, pip-audit, npm audit, cargo-audit, govulncheck, bundle-audit |
| Pentest | Can the running application be attacked? | Strix, run by a person |

Each layer reports **clean**, **findings**, **error** or **NOT RUN**. NOT RUN means unknown, never clean.

## Process
1. Run `sdd security`. Read every line, including the notes.
2. **Secrets findings.** Each shows kind, file, line and a fingerprint, never the value.
   - A real secret: tell the person to **revoke it at the provider first**. Removing the line is not enough; history still has it. Then remove it and, if it is in history, tell them it must be rewritten out or the key stays compromised.
   - A fake value (fixture, documentation): `sdd security allow <fingerprint> --reason "..."`, or put `sdd:allow-secret` on that line. Never accept a finding you have not looked at.
3. **Code-scan and dependency findings.** Read the tool's output. For each: fix now, or record an accepted risk with a named person and an expiry in `verification.md`. A fix gets a regression test.
4. **NOT RUN layers.** Say exactly which tool to install for this stack (the gate names them). Do not install tools yourself; ask. If the team decides not to run a layer, they switch it off with `sdd lifecycle skip <check> --reason "..."` and every report says so.
5. **Before ship:** `sdd security --strict`. In strict mode an enabled layer that did not run fails the gate.
6. **Pentest** is run by a person: see the `security-pentest` skill.
7. Record the gate result in `verification.md` under Security: date, each layer's status, and the disposition of every finding.

## About "as good as TruffleHog"
The built-in scanner covers the whole working tree and every line ever added in git history, with provider-specific detectors. It does not contact providers, so it cannot say whether a key is still live, and it has fewer detectors. When TruffleHog is installed the gate uses it instead, with live verification off unless the person passes `--verify-live`. Say which engine ran when you report.

## Security requirements from the spec
When a spec touches sign-in, permissions, user input, files, payments or personal data, each such requirement gets an abuse case written as its own requirement (`REQ-S01: If a user requests another user's invoice, then the service shall refuse`). Those get tasks and negative tests like any other requirement, and they tell the person what to aim the pentest at.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "The secret scan passed, so we're secure" | It finds leaked keys. It says nothing about injection, broken access control or vulnerable packages. |
| "No analyser is installed, so nothing was found" | NOT RUN is unknown. Report it as unknown. |
| "It's only in an old commit" | History is public to anyone with the repository. Revoke the key. |
| "Accept the finding so the gate goes green" | Accepting a real secret hides a breach. Look first. |

## Red Flags
- A finding accepted with no reason, or by the agent without the person
- A report that says "secure" while a layer is NOT RUN
- A leaked key removed from the file but not revoked
- Tools installed without asking

## Verification
- [ ] Every layer's status is reported by name, with the engine used for secrets
- [ ] Every finding has a disposition
- [ ] `sdd security --strict` passes, or each missing layer is switched off with a recorded reason
