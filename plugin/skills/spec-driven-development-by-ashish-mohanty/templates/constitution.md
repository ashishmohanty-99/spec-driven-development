# Constitution — {{PROJECT}}

Status: draft
<!-- A human changes this to "Status: ratified" after review. Agents must not. -->

The constitution is the small set of rules every spec, plan and change must obey. Keep it short
(under ~40 lines of rules). Each rule must be checkable. Derive from `.sdd/codebase-profile.md`
and from what the team already enforces; do not invent aspirations.

## 1. Quality bar
- Tests: <!-- e.g. every REQ has at least one automated test that names its id -->
- Required commands before a task is done: <!-- lint / typecheck / test commands from the profile -->
- Coverage or mutation expectations: <!-- or "none; judged in review" -->

## 2. Architecture invariants
- <!-- e.g. "Controllers never call the database directly" -->

## 3. Security and data
- Secrets never enter prompts, specs, logs or commits.
- Protected paths (see profile) are never read, printed or edited by agents.
- Model/API keys live only in environment variables or the CI secret store. `sdd audit` must pass.
- Security-relevant changes (auth, input handling, new endpoints) require a pentest record before ship.
- <!-- PII, auth, tenancy rules -->

## 4. Change boundaries
- **Always:** <!-- e.g. follow existing naming; update the spec when behaviour changes -->
- **Ask first:** <!-- e.g. new dependency, schema migration, public API change -->
- **Never:** <!-- e.g. disable a test to pass CI, edit generated files, force-push -->

## 5. Process
- Gates: spec approval, plan approval, task list approval, verify, ship. Humans approve.
- Branch / commit / PR conventions: <!-- from CONTRIBUTING or git log -->
- Definition of done: <!-- link to a checklist or list 4-6 items -->

## 6. Amendments
Record changes here with date and reason. A rule that is routinely ignored is removed or fixed.
