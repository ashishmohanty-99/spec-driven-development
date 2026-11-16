# CLI Reference

```text
sdd [--dir PATH] <command> [options]
```

`--dir` may go before or after the command. Also available as `specpilot` and `python -m specpilot`.

| Command | What it does | Exit codes |
|---|---|---|
| `sdd init [--agent claude\|generic] [--force] [--vendor]` | Profile the repo; install skills, commands, templates, e2e scaffolding; harden `.gitignore`. `--force` refreshes skills, commands, subagents and templates only. `--vendor` copies (or refreshes) the CLI in `.sdd/bin/` | 0, 1 |
| `sdd next` | The single next action for the repository and every feature | 0 |
| `sdd questions [--json]` | Setup questions the tool could not answer by itself | 0 |
| `sdd answer <id> <value>` | Record one answer (`stack`, `test-command`, `e2e-framework`, `base-url`, `lifecycle`) | 0, 1 |
| `sdd lifecycle [show]` | Every optional check, on or off, with what skipping costs | 0 |
| `sdd lifecycle skip <check> --reason "..."` | Switch a check off; prints the consequence and records the reason | 0, 1 |
| `sdd lifecycle enable <check>` | Switch it back on | 0, 1 |
| `sdd scan` | Refresh `.sdd/codebase-profile.md` (keeps your "Human-supplied context") | 0 |
| `sdd new <feature>` | Create `.sdd/specs/<feature>/spec.md` | 0, 1 |
| `sdd status` | Phase and progress of every feature | 0, 1 |
| `sdd verify [feature] [--strict]` | Gates: approval order, open questions, placeholders, REQ → task → test, shipped means finished, secrets | 0 ok, 1 errors |
| `sdd gen-tests <feature>` | Generate acceptance tests from the spec's scenarios in the configured form (`.py`, `.spec.ts` or `.feature`) | 0, 1 |
| `sdd regression [--strict] [--pentest TARGET --authorized]` | Unit tests + e2e + all gates (+ scan) | 0 ok, 1 failed |
| `sdd pentest --target T [--target T2] --authorized [--fail-on LEVEL] [--scan-mode quick\|standard\|deep] [--diff-base REF] [--max-budget USD] [--instruction TEXT]` | Guarded Strix scan | 0 clean, 1 error, 2 findings, **3 not run** |
| `sdd audit` | Security self-check of the SDD setup | 0 ok, 1 failed |
| `sdd doctor` | Installation health | 0, 1 |

## Slash commands (in your agent)

| Command | Phase |
|---|---|
| `/sdd-setup` | Guided setup |
| `/sdd-scaffold` | New project structure |
| `/sdd-next` | Any |
| `/sdd-init` | Discover |
| `/sdd-constitution` | Constitute |
| `/sdd-spec <idea>` | Specify |
| `/sdd-clarify <feature>` | Clarify |
| `/sdd-plan <feature>` | Plan |
| `/sdd-tasks <feature>` | Tasks |
| `/sdd-build <feature>` | Build |
| `/sdd-gen-tests <feature>` | Test automation |
| `/sdd-regression` | Verify |
| `/sdd-verify <feature>` | Verify |
| `/sdd-pentest <target>` | Security |
| `/sdd-audit` | Security |
| `/sdd-ship <feature>` | Ship |
| `/sdd-sync <feature>` | Drift |
| `/sdd-status` | Any |

## `.sdd/config.json`

```json
{
  "version": 1,
  "specsDir": ".sdd/specs",
  "e2eDir": "tests/e2e",
  "strict": false,
  "requireTestsPerRequirement": true,
  "e2eFramework": "playwright-python",
  "baseUrl": "http://localhost:3000",
  "commands": { "test": "pytest", "e2e": null },
  "lifecycle": { "constitution": true, "clarify": true, "plan": true, "tasks": true, "tests": true,
                 "e2e": true, "secrets": true, "review": true, "pentest": true },
  "skipped": {},
  "envPassthrough": ["DATABASE_URL"],
  "pentest": { "allowedTargets": ["staging.example.com"], "failOn": "high", "scanMode": "quick" }
}
```

- `commands` run without a shell. Pipes and `&&` are not interpreted; use a script or Makefile target. A path such as `./scripts/test.sh` is relative to the project. `e2e: null` means the framework's default (`pytest <e2eDir>` or `npx playwright test <e2eDir>`); for Gherkin, set it to your Cucumber runner's command.
- `e2eFramework` is `playwright-python`, `playwright-ts` or `gherkin`; unset means detect from the codebase.
- `lifecycle` and `skipped` are written by `sdd lifecycle`; edit them through that command so the reason is recorded. A command that cannot start fails the run.
- A config file that is not valid JSON, or has a value of the wrong type, stops every command with an error.
- `envPassthrough` lists variable **names** your tests need. Values stay in your shell.
- Config must never contain a credential. `sdd audit` fails if it sees one.

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `SDD_BASE_URL` | e2e tests | App under test (default `http://localhost:3000`) |
| test-account variables (your own names) | your login helper | Test account |
| `SDD_E2E_STRICT=1` | e2e tests | Coverage gaps fail instead of skip (set by `--strict`) |
| `STRIX_LLM`, `LLM_API_BASE` | Strix | Model and endpoint |
| the model key | Strix | Hosted-model key. Never needed with a local model |

## File syntax the gates rely on

| File | Syntax |
|---|---|
| `spec.md` | `Status: draft` / `approved` / `shipped` · `- REQ-001: When …, the … shall …` · `[NEEDS CLARIFICATION: …]` · `- REQ-001 — Given …, when …, then …` |
| `tasks.md` | `- [ ] T-001 Title (covers: REQ-001, REQ-002)` |
| tests | Any test file that contains the requirement id |
