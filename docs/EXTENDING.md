# Extending SpecPilot for your organisation

Core files never contain organisation-specific logic. Put it in `.sdd/extensions/`, which `init`
never overwrites. Skills are written to read these files when they exist.

| File | Effect |
|---|---|
| `rules.md` | Extra rules checked in plan and verify (naming, compliance, tenancy, data residency) |
| `gates.md` | Extra gates for verify/ship, e.g. "link an approved change ticket", "security review done" |
| `tools.md` | How the agent calls your internal tools: command, arguments, expected output, failure meaning |
| `glossary.md` | Domain vocabulary used when specifying and clarifying |
| `templates/*.md` (under `.sdd/templates/`) | Replace the spec/plan/tasks/ADR templates; `sdd new` uses `.sdd/templates/spec.md` first |

## Example: wrapping an internal automation without exposing it
`.sdd/extensions/tools.md`:
```markdown
## Ticket sync
- Run: `corp-tickets link --spec .sdd/specs/<feature>/spec.md`
- Expect: exit 0 and a ticket key printed. Put the key in spec.md header as `Ticket: KEY-123`.
- If it fails: stop and ask the human; never fabricate a key.
```
The agent learns *how to call* the tool. The tool's code stays in your private repository.

## Example gate
`.sdd/extensions/gates.md`:
```markdown
- SHIP requires `Ticket:` header in spec.md and a link to the security review in the PR description.
```

## Sharing a customised distribution
Fork this repository, edit skills, and run `npm run lint:skills && npm test`. Use extensions instead
of edits where possible so you can pull upstream improvements.

## Adding a skill
1. `skills/<name>/SKILL.md` with `name` equal to the directory, a `description` ending in "Use when …".
2. Sections: Overview, Process, Common Rationalizations, Red Flags, Verification.
3. Add the route to `using-sdd` and (optionally) a `commands/sdd-<name>.md`.
4. `npm run lint:skills`.

## Keep private material out of committed extensions
Reference internal systems by name; never commit hostnames, tokens, customer data or proprietary code
in extension files when the repository is shared more widely than the data's audience.
