---
name: constitution
description: Drafts and amends the project constitution, the short set of checkable rules every spec, plan and change must obey, derived from the codebase profile. Use after discovery, when onboarding a repo to SDD, or when a rule is repeatedly violated or obsolete.
---

# Constitution

## Overview
The constitution makes quality decisions once so they are not re-argued per feature. It lives in `.sdd/constitution.md`. It is derived from what the codebase and CI already enforce, plus the team's stated boundaries. A human ratifies it.

## Process
1. Read the profile, CONTRIBUTING, CI config and any existing agent instructions.
2. Fill each section of the template. For every rule ask: **how would a reviewer or a command detect a violation?** If nobody can, rewrite or drop it.
3. Prefer rules backed by an existing tool (linter rule, CI check, architecture test). Mark those `(enforced: <tool>)`. Rules without enforcement are `(review)`.
4. Fill the Always / Ask first / Never lists from observed pain: past incidents, protected paths, migration rules.
5. Merge `.sdd/extensions/rules.md` if it exists; keep org-specific text there, not here, when the constitution is shared outside the org.
6. Keep it under about 40 rules. Long constitutions are ignored.
7. Save with `Status: draft`. Stop. The human changes it to `Status: ratified`.

## Amending
Change a rule only with a dated entry in section 6 stating the reason. If a rule is broken three times with no consequence, propose removal rather than tolerating decay.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "Add best practices from the internet" | Unenforceable generic rules dilute the real ones. |
| "Ratify it myself to unblock work" | Ratification is a human gate. |
| "More rules means more safety" | Past about 40, agents and people stop reading them. |

## Red Flags
- Rules that say "should be clean/maintainable" with no check
- No Never list
- Constitution contradicting CI

## Verification
- [ ] Each rule names its enforcement (tool) or is tagged (review)
- [ ] Always / Ask first / Never filled
- [ ] Status left as draft for the human
