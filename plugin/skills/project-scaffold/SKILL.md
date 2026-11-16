---
name: project-scaffold
description: "Creates a conventional, complete folder structure and working baseline for a new application in any language or framework, after agreeing the stack and layout with the user. Use when the repository is empty or has no application code, when the profile says project kind is greenfield, or when someone asks to start a new app, service, library or CLI from scratch."
---

# Project Scaffold

## Overview
An empty repository needs a real structure before any feature is specified: the layout the stack's own community uses, a build that runs, one passing test, and CI. This skill agrees that structure with the user, creates it with the stack's official tooling, and then hands over to the normal lifecycle. It works for any language: the conventions come from the ecosystem, not from this tool.

## Process
1. **Know the stack.** Read `project.stack` in `.sdd/config.json`. If it is empty, ask what they are building and with what, then `sdd answer stack "<answer>"`. If they have no preference, propose one mainstream option for their goal and say why.
2. **Ask only what changes the layout** (one at a time, recommended option first):
   - What kind of thing is it: web app, API/service, mobile app, CLI, library, data pipeline?
   - One deployable or several (front end + back end, services)? Monorepo or single package?
   - Package manager / build tool, if the ecosystem has more than one common choice.
   - Database or other infrastructure it must talk to.
3. **Propose the tree before creating anything.** Show the folder structure as a code block with one line per folder saying what lives there. Follow `references/Project-Structure.md` in the skill for the principles and the per-stack conventions. **Stop and wait for approval.**
4. **Create it with official tooling**, not by hand-writing boilerplate: the framework's own generator (`npm create`, `dotnet new`, `cargo new`, `go mod init`, `spring initializr`, `flutter create`, `rails new`, and so on), then adjust to the agreed tree. Adding the generator's dependencies is expected here; anything beyond that is an "ask first".
5. **Make the baseline real.** Before you call it done, all of these must run and pass:
   - install / restore dependencies
   - build or type-check
   - one meaningful smoke test using the stack's standard test framework
   - lint / format with the ecosystem's default tool
6. **Add the surroundings:** `README.md` (how to install, run, test), `.gitignore` for the stack (keep the rules `sdd init` added), `.env.example` with names only and no values, and a CI workflow that runs build, lint and tests.
7. **Refresh the tool's view.** Run `sdd scan`, then `sdd answer test-command "<the test command>"`, and check `sdd questions`.
8. **Report** the tree created, the commands that passed (with their output summary), and the next action from `sdd next`. Then stop: the first feature starts with `specify`.

## Structure principles (any language)
- Source, tests, configuration, scripts and documentation each have one obvious home.
- Group code by feature or domain once there is more than one; avoid top-level folders named after technical layers only (`utils`, `helpers`, `misc`).
- Dependencies point inward: UI and transport depend on domain logic, never the reverse.
- Tests mirror the source tree; acceptance tests live in the folder `sdd` prepared (`tests/e2e` by default).
- Nothing secret in the repository. Configuration is read from the environment.
- Generated and vendored code is separated and marked, so nobody edits it by hand.

## Common Rationalizations
| Rationalization | Reality |
|---|---|
| "I'll invent a clean structure" | Teams and tools expect the ecosystem's layout. Novelty costs every new joiner. |
| "Write the boilerplate by hand, it's quicker" | Official generators stay correct as frameworks change. Hand-written scaffolds rot. |
| "Tests and CI can come later" | A baseline without a passing test is not a baseline; the first feature inherits the gap. |
| "Start coding the feature while I'm here" | Scaffolding is not a feature. Features start from an approved spec. |

## Red Flags
- Files created before the user approved the tree
- A scaffold whose build or test command was never run
- Real values in `.env.example`, or a committed `.env`
- Feature code mixed into the scaffolding commit

## Verification
- [ ] The user approved the tree before it was created
- [ ] Install, build, lint and one test ran and passed (commands shown)
- [ ] README, `.gitignore`, `.env.example` and CI exist
- [ ] `sdd scan` shows the stack and `sdd next` points to the first spec
