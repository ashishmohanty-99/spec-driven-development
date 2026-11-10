---
name: codebase-discovery
description: Builds and validates a factual profile of an existing codebase (stack, commands, conventions, boundaries, test setup, hotspots) so later SDD phases fit the real project. Use on first install, after major restructuring, or when the profile has unverified CONFIRM items or looks stale.
---

# Codebase Discovery

## Overview
Specs written without knowing the stack are guesses. `npx specpilot scan` records facts detectable from manifests and file names. This skill adds the understanding a scanner cannot: conventions, seams, risk areas and the way this team actually works. Output: an accurate `.sdd/codebase-profile.md`.

## Process
1. **Run the scan.** `npx specpilot scan`, then read `.sdd/codebase-profile.md`.
2. **Resolve every CONFIRM item.** Run each detected command (build, test, lint) once. Record the real result: passes, fails, or needs setup. A command you did not run stays marked unverified.
3. **Read, do not skim, a small sample.** Open the entry point, one representative module per top-level directory, and one existing test. Identify:
   - Layering and dependency direction (who may import whom)
   - Naming, error-handling, logging and config conventions
   - Test style (unit vs integration, fixtures, naming)
   - Generated or vendored code agents must not edit
4. **Find the seams.** Where would a typical feature attach? Name 3 to 5 extension points with file paths.
5. **Find the hazards.** Flaky tests, slow suites, areas with no tests, files everyone fears. Use `git log --stat` frequency to spot hotspots if history exists.
6. **Read the human docs.** README, CONTRIBUTING, ADRs, existing AGENTS.md/CLAUDE.md. Where docs and code disagree, record both and flag it.
7. **Write findings** under "Human-supplied context" in the profile (it survives re-scans), in this shape:

```
### Conventions
- Errors: <pattern with path example>
### Seams
- <extension point> — <path>
### Hazards
- <hazard> — <path / evidence>
### Unverified
- <claim you could not confirm>
```
8. Stop. Ask the human to confirm the profile before the constitution phase.

## Rules
- Cite a path for every claim. No path, no claim.
- Never open files listed under "Protected paths".
- Do not change source code in this phase.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "The scan already did this" | It lists tools; it cannot tell you the layering rules or hazards. |
| "I'll learn conventions while coding" | That is how feature code ends up in the wrong layer. |
| "Running the tests takes too long" | Then record the suite as slow; an unrun suite is an unknown gate. |

## Red Flags
- Profile commands never executed
- Conventions described with no file example
- Large codebase "understood" after reading only the README

## Verification
- [ ] Every CONFIRM item is resolved or listed under Unverified
- [ ] At least one seam, one convention and one hazard recorded with paths
- [ ] Human confirmed the profile
