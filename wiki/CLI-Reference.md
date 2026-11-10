# CLI Reference

```text
sdd [--dir PATH] <command> [options]
```

`--dir` goes before the command. Also available as `specpilot` and `python -m specpilot`.

| Command | What it does | Exit codes |
|---|---|---|
| `sdd init [--agent claude\|generic] [--force]` | Profile the repo; install skills, commands, templates, e2e scaffolding; harden `.gitignore` | 0, 1 |
| `sdd scan` | Refresh `.sdd/codebase-profile.md` (keeps your "Human-supplied context") | 0 |
| `sdd new <feature>` | Create `.sdd/specs/<feature>/spec.md` | 0, 1 |
| `sdd status` | Phase and progress of every feature | 0, 1 |
| `sdd verify [feature] [--strict]` | Gates: approval order, open questions, placeholders, REQ → task → test, secrets | 0 ok, 1 errors |
| `sdd gen-tests <feature>` | Generate `tests/e2e/test_<feature>.py` from acceptance scenarios | 0, 1 |
| `sdd regression [--strict] [--pentest TARGET --authorized]` | Unit tests + e2e + all gates (+ scan) | 0 ok, 1 failed |
| `sdd pentest --target T [--target T2] --authorized [--fail-on LEVEL] [--scan-mode quick\|standard\|deep] [--diff-base REF] [--max-budget USD] [--instruction TEXT]` | Guarded Strix scan | 0 clean, 1 error, 2 findings, **3 not run** |
| `sdd audit` | Security self-check of the SDD setup | 0 ok, 1 failed |
| `sdd doctor` | Installation health | 0, 1 |

## Slash commands (in your agent)

| Command | Phase |
|---|---|
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
  "commands": { "test": "pytest", "e2e": "pytest tests/e2e" },
  "envPassthrough": ["DATABASE_URL"],
  "pentest": { "allowedTargets": ["staging.example.com"], "failOn": "high", "scanMode": "quick" }
}
```

- `commands` run without a shell. Pipes and `&&` are not interpreted; use a script or Makefile target.
- `envPassthrough` lists variable **names** your tests need. Values stay in your shell.
- Config must never contain a credential. `sdd audit` fails if it sees one.

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `SDD_BASE_URL` | e2e tests | App under test (default `http://localhost:3000`) |
| `SDD_UI_USER`, `SDD_UI_PASS` | your `ui_login.py` | Test account |
| `SDD_E2E_STRICT=1` | e2e tests | Coverage gaps fail instead of skip (set by `--strict`) |
| `STRIX_LLM`, `LLM_API_BASE` | Strix | Model and endpoint |
| `LLM_API_KEY` | Strix | Hosted-model key. Never needed with a local model |

## File syntax the gates rely on

| File | Syntax |
|---|---|
| `spec.md` | `Status: draft` / `approved` / `shipped` · `- REQ-001: When …, the … shall …` · `[NEEDS CLARIFICATION: …]` · `- REQ-001 — Given …, when …, then …` |
| `tasks.md` | `- [ ] T-001 Title (covers: REQ-001, REQ-002)` |
| tests | Any test file that contains the requirement id |
