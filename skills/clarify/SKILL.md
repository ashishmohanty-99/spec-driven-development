---
name: clarify
description: Resolves open questions and ambiguities in a draft spec through targeted questions, then records decisions so the spec can be approved. Use when a spec contains [NEEDS CLARIFICATION] markers, before spec approval, or when requirements conflict or feel underspecified.
---

# Clarify

## Overview
An unresolved ambiguity becomes a wrong guess in code. This phase removes them cheaply, before planning, with the fewest possible questions.

## Process
1. List every `[NEEDS CLARIFICATION]` marker, then scan the spec for hidden ones: undefined terms, missing error cases, unstated actors, conflicting requirements, unmeasurable adjectives, missing non-goals.
2. **Try to answer from evidence first.** Code, tests, docs, glossary, git history. If found, resolve it yourself and log the source in the decision log.
3. **Rank the rest** by impact (changes data model or public behaviour first, cosmetic last). Ask at most five at a time.
4. **Ask one question each, with options.** Give 2 to 4 concrete choices, your recommendation first with a reason, and what each choice changes in the spec.
5. **Apply answers.** Edit the requirement, delete the marker, add a decision-log row (date, decision, reason). Add new `REQ-` ids rather than renumbering.
6. Re-run `npx specpilot verify <feature>`. Repeat until no markers remain.
7. Tell the human the spec is ready for approval. **Stop.** They set `Status: approved`.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "Ask everything now" | A wall of questions gets skimmed. Ask the highest-impact few. |
| "Pick the likely answer and move on" | That is the failure this phase exists to prevent. |
| "Delete the marker, it's minor" | Minor now, rework later. Resolve it or keep it visible. |

## Red Flags
- Markers deleted without a decision-log entry
- Questions that the codebase already answers
- Requirement ids renumbered

## Verification
- [ ] No `[NEEDS CLARIFICATION]` markers remain
- [ ] Each decision logged with reason
- [ ] Human has been told the spec awaits approval
