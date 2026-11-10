# SpecPilot — Build Plan

Goal: an installable Spec-Driven Development (SDD) kit for the AI SDLC. Anyone installs it, it
profiles their codebase, and their AI agent then works inside a gated spec → plan → tasks →
build → verify → ship framework, with guidance on how to use it.

## Design principles
1. **Codebase-aware first.** Specs written without knowing the stack, commands and conventions
   are guesses. `discover` produces a profile every later phase reads.
2. **Gates are mechanical where possible.** Traceability (REQ → task → test) and open-question
   checks are enforced by a zero-dependency CLI, not by agent goodwill.
3. **Agent-neutral.** Skills follow the open `SKILL.md` format; installs for Claude Code, and
   via `AGENTS.md` for Codex, Cursor, Copilot, Gemini and others.
4. **Org-neutral by construction.** Nothing org-specific ships in core. Org rules, templates and
   hooks plug in through `.sdd/extensions/` (see `docs/EXTENDING.md`).
5. **Local and private.** The scanner reads file names and manifests only, never `.env`
   contents, and makes no network calls.

## Deliverables
| # | Item | Status |
|---|------|--------|
| 1 | Zero-dependency CLI `sdd` (`init`, `scan`, `new`, `status`, `verify`, `gen-tests`, `regression`, `pentest`, `doctor`) | done |
| 2 | Codebase scanner → `.sdd/codebase-profile.md` + `.json` | done |
| 3 | 13 skills covering discover → ship, plus meta router | done |
| 4 | Slash commands `/sdd-*` (14) | done |
| 5 | Reviewer subagents | done |
| 6 | Templates (constitution, spec, plan, tasks, ADR) | done |
| 7 | Extension mechanism for org-specific adapters | done |
| 8 | Docs: getting started, user guide, architecture, extending | done |
| 9 | Tests (node:test) + CI + skill linter | done |
| 10 | Spec → Playwright regression generator (`gen-tests`), UI connector fixtures | done |
| 11 | Regression runner (`regression`) unifying unit + e2e + gates in one exit code | done |
| 12 | Penetration-testing gate (`pentest`) wrapping Strix (usestrix/strix), not vendored | done |

## Lifecycle
```
DISCOVER → CONSTITUTE → SPECIFY → CLARIFY → PLAN → TASKS → BUILD → VERIFY → SHIP
 profile    guardrails   REQ-ids   gate      design  T-ids   TDD     trace    DoD
                                                               │
                                                     gen-tests ┴ regression ┴ pentest
                                                     (spec → Playwright e2e → security scan)
```

## Not in scope (honest limits)
- No hosted service. "SaaS-like" here means: install with one command, no infrastructure.
  A hosted dashboard would sit on top of the `.sdd/` files; the formats are stable for that.
- Your private automation was not visible to me; extension points are defined so you can
  wrap it without it entering this repo.
- Strix is called as a CLI, not vendored: it needs Docker and its own LLM key, and its source is
  not copied into this repository. "Bundled" here means a consistent command and gate, not a fork.
