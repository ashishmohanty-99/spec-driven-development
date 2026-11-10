---
name: specify
description: Turns an idea or change request into a structured, testable spec with permanent REQ ids, EARS-style requirements, non-goals and boundaries, grounded in the codebase profile. Use when starting a feature or significant change and no approved spec exists.
---

# Specify

## Overview
The spec is the contract between human and agent: what we are building, how we will know it is done, and what we will not touch. Write it before code, ground it in the real codebase, and make every requirement testable.

## Process
1. **Load context.** Profile, constitution, extensions, glossary. Search the repo for existing behaviour related to the request; cite paths in section 3.
2. **Create the file.** `sdd new <feature-kebab-name>` then edit `.sdd/specs/<feature>/spec.md`.
3. **Decompose if needed.** If the request bundles several independently testable capabilities (separate user outcomes, separate data models), do not write one giant spec. Propose a capability map first: module ids, one-line purpose, dependency direction, build order. Get it approved, then specify one module per spec.
4. **Objective and scope.** Outcome for a named user. Non-goals are mandatory; at least two, or write "none identified" and justify.
5. **Requirements in EARS form.** One behaviour per line: `REQ-001: When <trigger>, the <system> shall <response>`. Each must be falsifiable by a test. Replace vague words (fast, secure, intuitive) with measurable thresholds.
6. **Non-functional requirements** only where they matter (latency, accessibility, audit). Use ids `REQ-N01`.
7. **Acceptance scenarios** for anything where the EARS line alone is ambiguous.
8. **Boundaries.** Always / Ask first / Never, consistent with the constitution.
9. **Mark unknowns.** Every assumption you cannot confirm from the code or the user becomes `[NEEDS CLARIFICATION: question]`. Do not invent answers.
10. Save. Leave `Status: draft`. Summarise requirement count and open questions. **Stop.**

## Quality test for a requirement
- Could two engineers write different tests and both claim to satisfy it? Tighten it.
- Does it mix two behaviours? Split it and give each an id.
- Does it dictate implementation ("use Redis")? Move that to the plan.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "I'll fill the gaps sensibly" | Gaps are exactly where agents diverge from intent. Mark them. |
| "Requirements will change" | Ids are stable and the spec is living; change it deliberately. |
| "Write the spec and plan together to save time" | Reviewing intent and design separately is the whole point. |
| "Non-goals are obvious" | They are what stop scope creep mid-build. |

## Red Flags
- Requirements with "should", "etc.", "appropriate", "fast"
- No cited paths in section 3 for a change to existing code
- Spec and plan produced in one turn
- Zero open questions on a vague request

## Verification
- [ ] `sdd verify <feature>` shows no ERROR
- [ ] Every requirement is testable and has a stable id
- [ ] Non-goals and boundaries are present
- [ ] Turn ended with the spec saved as draft
