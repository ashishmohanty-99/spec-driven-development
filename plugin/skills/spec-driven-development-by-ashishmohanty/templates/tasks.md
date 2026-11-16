# Tasks: {{FEATURE}}

Plan: `plan.md`. Order by dependency. Each task is a vertical slice that leaves the build green.
Size: one focused session, at most ~5 files. Every task must name the requirement(s) it covers.

Format: `- [ ] T-001 Short imperative title (covers: REQ-001, REQ-002)`

- [ ] T-001 <title> (covers: REQ-001)
  - Acceptance: <what is true when done>
  - Verify: <command or check>
  - Files: <paths>
  - Depends on: none

## Checkpoints
- After T-00X: run the full test command and review before continuing.
