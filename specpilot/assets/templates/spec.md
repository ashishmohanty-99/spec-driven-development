# Spec: {{FEATURE}}

Status: draft
<!-- draft → approved. Only a human sets "approved". Plan and tasks are blocked until then. -->

## 1. Objective
What problem does this solve, for whom, and why now? Two to five sentences. State the user-visible outcome.

## 2. Scope
- **In scope:**
- **Out of scope (explicit non-goals):**

## 3. Context from the codebase
Existing modules, patterns, and constraints this feature touches (cite paths). Link `.sdd/codebase-profile.md` facts you rely on.

## 4. Requirements
Write each as one testable statement using EARS patterns. IDs are permanent: never renumber.
- Ubiquitous: `The <system> shall <response>`
- Event: `When <trigger>, the <system> shall <response>`
- State: `While <state>, the <system> shall <response>`
- Unwanted: `If <condition>, then the <system> shall <response>`
- Optional: `Where <feature included>, the <system> shall <response>`

- REQ-001: When …, the … shall …
- REQ-002: If …, then the … shall …

## 5. Non-functional requirements
- REQ-N01: <!-- performance, security, accessibility, observability; make them measurable -->

## 6. Acceptance scenarios
One Given/When/Then per requirement that is not obvious from its EARS text. Reference the REQ id with a dash, never a colon: a colon (`REQ-001:`) defines a requirement.
- REQ-001 — Given …, when …, then …

## 7. Boundaries
- **Always:**
- **Ask first:**
- **Never:**

## 8. Open questions
Mark every unresolved assumption inline with `[NEEDS CLARIFICATION: question]`. Approval is blocked while any remain.

## 9. Decision log
| Date | Decision | Reason |
|---|---|---|
