# Architecture

## Layers
```
┌─────────────────────────── Agent (Claude Code, Codex, Cursor …) ──────────────────────────┐
│  /sdd-* commands ──▶ skills (process, judgement) ──▶ subagents (independent review)       │
└──────────────▲──────────────────────────────────────────────────────▲─────────────────────┘
               │ reads                                                  │ calls, exit codes
        .sdd/ (files in git)                                    sdd CLI (deterministic)
  profile · constitution · specs/<f>/{spec,plan,tasks,verification}.md · adr · extensions
```
- **Skills** carry process and judgement (what good looks like, rationalizations to refuse).
- **The CLI** carries facts and gates (stack detection, traceability, approval ordering). Anything
  that can be checked deterministically is checked by code, not trusted to the model.
- **`.sdd/` files** are the only shared state. Plain markdown and JSON, reviewable in PRs, stable
  formats that other tools (dashboards, trackers) can read.

## Data model
| Artifact | Key syntax | Parsed by |
|---|---|---|
| Spec | `Status: draft\|approved`, `- REQ-001: …`, `[NEEDS CLARIFICATION: …]` | `lib/spec.js` |
| Tasks | `- [ ] T-001 title (covers: REQ-001, REQ-002)` | `lib/spec.js` |
| Tests | any test file containing `REQ-###` | `lib/spec.js` |
| Profile | `codebase-profile.json` (+ rendered `.md`) | `lib/scan.js` |

Parsers ignore fenced code and HTML comments so examples never count as requirements.

## Gate rules enforced by `sdd verify`
1. Spec defines ≥1 requirement, ids unique, no placeholder text.
2. Plan or tasks present ⇒ spec is `approved`; tasks present ⇒ plan present.
3. Open clarification markers are errors once a plan exists, warnings before.
4. Every requirement covered by ≥1 task; every task covers ≥1 existing requirement.
5. Completed tasks' requirements are named by a test (warning; error with `--strict` or config `strict`).

Human approval itself is not mechanisable: the status line is a convention enforced by process and review.

## Design decisions
- **Zero dependencies, Node ≥18:** installs anywhere `npx` works, nothing to audit or update.
- **Names and manifests only in scans:** minimises exposure of proprietary code and secrets.
- **Dual install target:** `.claude/` for Claude Code; `.agents/` + `AGENTS.md` for the rest.
- **Extensions by convention, not config:** drop markdown into `.sdd/extensions/`; skills read it.
  Keeps core upgradable (`init --force`) without merging org changes.
- **Not hosted:** "SaaS-like" delivery is a one-command install. A hosted dashboard can read `.sdd/`
  without any format change.

## Limits
- Detection covers common ecosystems; unknown stacks fall back to what the human writes in the profile.
- Test linkage is textual (id mentioned in a test file), not proof the assertion is meaningful. The
  `verify` skill and `spec-reviewer` cover that judgement.
