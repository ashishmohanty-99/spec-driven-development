# Troubleshooting

## Gates

| Message | Meaning | Fix |
|---|---|---|
| `plan/tasks exist but spec.md is not "Status: approved"` | A gate was skipped | A human sets the status line. Agents must not |
| `REQ-00X is not covered by any task` | A requirement would never be built | Add `(covers: REQ-00X)` to a task |
| `T-00X references no requirement` | Work nobody asked for | Link it, or delete it |
| `has completed task(s) but no test file names it` | Built but unproven | Put the id in a test name, marker or comment; or run `sdd gen-tests` |
| `placeholder text left in REQ-00X` | Template text was approved | Replace `…`, `<…>`, `TBD` |
| `SECURITY: possible … in spec.md:12` | A credential shape was found | Remove it **and rotate the credential** |
| Requirement not detected | Wrong syntax | Definitions use a colon: `- REQ-001: …`. Scenarios use a dash: `- REQ-001 — Given …` |

## Tests

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: playwright` | `pip install pytest-playwright && playwright install chromium` |
| Test skipped: `no UI step matches: '…'` | Rephrase with a [built-in phrase](Test-Automation#3-built-in-phrases-work-with-no-code) or add an `@step` |
| Test skipped: `scenario needs a logged-in user` | Create `.sdd/extensions/ui_login.py` from the example |
| Unit tests fail only under `sdd regression` | They need an environment variable. Add its **name** to `envPassthrough` |
| `commands.test` with `&&` does nothing useful | Commands run without a shell. Point to a script or Makefile target |

## Pentest

| Message | Fix |
|---|---|
| `PENTEST NOT RUN (exit 3)` + "No model is configured" | Set up a local model (no key), or export `STRIX_LLM` and `LLM_API_KEY` in your shell |
| `…is not in pentest.allowedTargets` | Someone authorised to test that host adds it to `.sdd/config.json` |
| `Pass --authorized` | Confirms you may test every target |
| `Refusing to send LLM_API_KEY over plain http` | Use an `https://` API base |
| `Strix is not installed` | `pipx install strix-agent`; Docker must be running |

## Agent behaviour

| Symptom | Fix |
|---|---|
| Agent starts coding without a spec | Check `CLAUDE.md` / `AGENTS.md` contains the SpecPilot block; run `sdd doctor` |
| Agent approved its own spec | Revert the status line. Report it; the skills forbid this |
| Agent asks for your API key | Do not give it. It is told never to ask; the command is yours to run |
| Profile has wrong commands | Correct them under "Human-supplied context"; re-scans keep that section |

## FAQ

**Is this a hosted service?** No. It is a package you install; everything stays in your repository. That is also why your key never has to go anywhere.

**Does it work without Claude?** Yes: `sdd init --agent generic` writes `AGENTS.md` and `.agents/skills`.

**Can I use it on legacy code with no specs?** Yes. `/sdd-sync` writes a baseline spec of observed behaviour for one capability at a time.

**How do I upgrade?** Reinstall the package, then `sdd init --force`. Your `.sdd/extensions/`, specs and config are kept.
