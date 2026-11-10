# SpecPilot

**Codebase-aware Spec-Driven Development for the AI SDLC.**
Install it into any repository. It profiles your code, then guides your AI agent (and you) through
a gated lifecycle where nothing is built without an approved, testable spec, and every requirement is
traceable to a task and a test.

```
DISCOVER → CONSTITUTE → SPECIFY → CLARIFY → PLAN → TASKS → BUILD → VERIFY → SHIP
 profile    guardrails   REQ ids   gate      design  T ids   TDD     trace    DoD
              └──────────── human approves at every arrow ─────────────┘
```

## Why it exists
AI agents fail on real codebases for two reasons: they guess at requirements, and they don't know
the project's conventions. SpecPilot addresses both:

1. **It reads your codebase first** (`sdd scan` + the `codebase-discovery` skill) and writes a profile
   of stack, commands, conventions, seams, hazards and protected paths that every later phase uses.
2. **It enforces the gates mechanically** (`sdd verify`): no plan before an approved spec, no
   unresolved questions, no placeholder text, every requirement covered by a task and, once built,
   named by a test. Agents cannot talk their way past a failing exit code.
3. **It turns the spec into regression and security coverage, not just prose.** `sdd gen-tests`
   reads a spec's acceptance scenarios and generates a Playwright test per requirement, wired to
   your app through one small UI connector file. `sdd regression` runs that suite plus the
   project's own tests plus the traceability gates as one CI check. `sdd pentest` wraps the
   open-source [Strix](https://github.com/usestrix/strix) AI pentester as the same kind of gate for
   security, so the full AI SDLC — spec, build, functional regression, and a penetration test — is
   one package instead of four separately wired tools.

## Install (about 2 minutes)
Requires Node 18+. No dependencies, no network calls, no account.

```bash
# in your repository root
npx specpilot init            # Claude Code (default)
npx specpilot init --agent generic   # Codex, Cursor, Copilot, Gemini, etc. via AGENTS.md
```

> Until published to npm, run it from a clone: `node /path/to/spec-driven-development/bin/sdd.js init`.

Or as a Claude Code plugin:

```
/plugin marketplace add ashishmohanty-99/spec-driven-development
/plugin install specpilot@specpilot-marketplace
```

`init` creates: `.sdd/` (config, profile, constitution draft, templates, extensions), skills and
`/sdd-*` commands for your agent, and a managed block in `CLAUDE.md` / `AGENTS.md`. It never
overwrites your files without `--force`.

## Use it
```text
/sdd-init                     profile the codebase, confirm with you
/sdd-constitution             draft guardrails; you ratify
/sdd-spec  "rate-limit logins"   write the spec (REQ ids, non-goals)       ← you approve
/sdd-clarify login-rate-limit    close open questions                       ← you approve
/sdd-plan  login-rate-limit      technical plan mapped to code              ← you approve
/sdd-tasks login-rate-limit      small traceable tasks                      ← you approve
/sdd-build login-rate-limit      one task, test-first, committed
/sdd-gen-tests login-rate-limit  generate the Playwright e2e suite from the spec
/sdd-regression                  unit + e2e + traceability gates, one exit code
/sdd-pentest --target https://staging.example.com   Strix security scan (opt-in; needs Docker + LLM key)
/sdd-verify login-rate-limit     prove every REQ, independent review
/sdd-ship  login-rate-limit      readiness + rollback, you merge
```
Full walkthrough with a worked example: **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)**.

## Regression and security testing
- `npx specpilot gen-tests <feature>` generates `tests/e2e/<feature>.spec.js` from the spec's
  acceptance scenarios — one Playwright test per requirement, named with its `REQ-` id so it counts
  toward `sdd verify`'s coverage. Wire it to your app once in `tests/support/ui-connector.js`
  (and `.sdd/extensions/ui-login.js` for authenticated flows); regeneration keeps anything you add
  below the generated block.
- `npx specpilot regression [--strict] [--pentest <target>]` is the single CI entry point: the
  project's own test script, the generated Playwright suite, every feature's traceability gate, and
  optionally a Strix scan, in one exit code.
- `npx specpilot pentest --target <path|url> [--fail-on high]` wraps
  [Strix](https://github.com/usestrix/strix) (Apache-2.0), an open-source AI pentesting agent. It is
  not vendored — install it once with `curl -sSL https://strix.ai/install | bash`, set `STRIX_LLM`
  and `LLM_API_KEY`, keep Docker running. Without Strix installed or without credentials, the
  command reports a **skip**, never a false pass. Only scan systems you own or are authorized to test.

## What's inside
| Path | What |
|---|---|
| `bin/sdd.js`, `lib/` | Zero-dependency CLI: `init scan new status verify gen-tests regression pentest doctor` |
| `skills/` | 13 skills (router + one per phase + spec-sync, test-automation, security-pentest) |
| `commands/` | 14 `/sdd-*` slash commands |
| `agents/` | `spec-reviewer` (independent diff review), `codebase-cartographer` (read-only mapper) |
| `templates/` | constitution, spec (EARS), plan, tasks, ADR |
| `ui/` | Playwright config + UI connector fixture installed to the project root |
| `docs/` | [User guide](docs/USER_GUIDE.md) · [Architecture](docs/ARCHITECTURE.md) · [Extending for your org](docs/EXTENDING.md) · [Plan](docs/PLAN.md) |

## Privacy and safety
- Scans read **file names and manifests only**; secret-like files (`.env`, keys) are listed as
  protected and never opened.
- Everything stays local in `.sdd/`. There is no telemetry and no network access.
- Org-specific rules, tools and gates go in `.sdd/extensions/`, never in the core files.

## Development
```bash
npm test               # CLI + parser tests (node:test)
npm run lint:skills    # frontmatter + required sections for every skill, agent, command
```

## Credits
The gated lifecycle and skill format draw on ideas from
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT). SpecPilot is an
independent implementation that adds codebase profiling, mechanical traceability gates and
organisation extension points.

## License
MIT
