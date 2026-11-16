# Getting Started

Time: about 10 minutes. You need Python 3.11+ and an AI coding agent (Claude Code, Codex, Cursor, Copilot, Gemini CLI).

## 1. Install

```bash
npx skills add ashishmohanty-99/spec-driven-development
```

This one command installs the `specpilot` skill into Claude Code, Cursor, Codex, Copilot, Gemini CLI and other agents that support skills. Nothing else is needed: the skill carries its own tool.

```mermaid
flowchart LR
    A["npx skills add<br/>ashishmohanty-99/spec-driven-development"] --> B["Ask your agent:<br/>Set up SpecPilot in this repository"]
    B --> C["Skill runs its bundled tool<br/>sdd init --vendor"]
    C --> D([Repository ready<br/>tool lives in .sdd/bin/])
    D --> E["Teammates: git pull<br/>nothing to install"]
```

| Other route | How |
|---|---|
| Claude Code plugin | `/plugin install specpilot --marketplace ashishmohanty-99/spec-driven-development` |
| Python package | `pipx install git+https://github.com/ashishmohanty-99/spec-driven-development` |
| claude.ai | Clone the repository, run `python tools/build_skill.py`, upload `dist/specpilot-skill.zip` at Customize → Skills |

The tool needs Python 3.11+ and has no third-party dependencies. After setup it lives in your project at `.sdd/bin/`; wherever this guide says `sdd`, run `python3 .sdd/bin/sdd.py` (or plain `sdd` if you installed the Python package).

## 2. Initialise your repository

Ask your agent **"Set up SpecPilot in this repository"**, or run it yourself:

```bash
cd your-project
sdd init --vendor                 # Claude Code
sdd init --vendor --agent generic # any other agent (writes AGENTS.md and .agents/skills)
```

```mermaid
flowchart TD
    I[sdd init] --> P[".sdd/codebase-profile.md<br/>stack, commands, protected paths"]
    I --> C[".sdd/constitution.md<br/>draft rules"]
    I --> S[".claude/skills + commands<br/>the process for your agent"]
    I --> T["tests/e2e/ui_connector.py<br/>bridge to your UI"]
    I --> G[".gitignore hardened<br/>.env, keys, scan output"]
    I --> M["CLAUDE.md / AGENTS.md<br/>managed block"]
```

`init` never overwrites your files unless you pass `--force`, and it only reads file names and manifests. It does not open `.env` or key files.

## 3. Confirm the setup

```bash
sdd doctor   # is everything installed?
sdd audit    # any secrets or risky config?
```

## 4. Teach it your codebase (once)

In your agent:

| You type | The agent does | You check |
|---|---|---|
| `/sdd-init` | Runs the detected commands, reads sample modules, records conventions and hazards in the profile | Commands and conventions are right |
| `/sdd-constitution` | Drafts rules from what your repo already enforces | Edit, then set `Status: ratified` yourself |

## 5. Ship your first feature

```text
/sdd-spec "Lock an account for 15 minutes after 5 failed logins"
/sdd-clarify login-lockout      → you set Status: approved in spec.md
/sdd-plan login-lockout         → you approve
/sdd-tasks login-lockout        → you approve
/sdd-build login-lockout        → repeat per task
/sdd-gen-tests login-lockout
/sdd-verify login-lockout
/sdd-ship login-lockout         → you merge
```

Each command stops at a gate and waits for you. The full walkthrough, with what to look for at each gate, is in [Step-by-Step Workflow](Step-by-Step-Workflow).

## 6. Add it to CI

```yaml
permissions:
  contents: read
steps:
  - uses: actions/checkout@v4
  - run: pip install git+https://github.com/ashishmohanty-99/spec-driven-development
  - run: sdd audit
  - run: sdd regression --strict
```

> **Next:** [Step-by-Step Workflow](Step-by-Step-Workflow)
