# Manual Mode

The `sdd` tool automates the checks, but the method does not depend on it. When no tool is available (for example, when this skill was installed from a plugin directory that carries documentation only), the agent does each command's job by hand, exactly as described here. The files and their formats are the same either way, so a team can add the tool later without changing anything.

## When to use it

Use the first that applies:

1. `python3 .sdd/bin/sdd.py` exists in the repository: use it.
2. `sdd --version` works: use it.
3. Neither: work in manual mode. Tell the person once that an optional open-source tool automates these checks, that its source is in the skill's repository, and that installing it is their decision. Do not install anything yourself.

## What each command does, by hand

| Command | Do this instead |
|---|---|
| `sdd init` | Create the files in "Setup by hand" below |
| `sdd scan` | Re-read the manifests and update `.sdd/codebase-profile.md` |
| `sdd questions` / `sdd answer` | Ask the five setup questions; write the answers into `.sdd/config.json` |
| `sdd lifecycle` | Read `lifecycle` in `.sdd/config.json`; to switch a check off, state its cost, get the person's reason, then set it to `false` and add the reason and date under `skipped` |
| `sdd new <feature>` | Copy `templates/spec.md` from this skill to `.sdd/specs/<feature>/spec.md` |
| `sdd status` / `sdd next` | Read each feature's files and apply "Which phase is a feature in" |
| `sdd verify` | Apply "The gates" to each feature and report every failure |
| `sdd gen-tests` | Write one acceptance test per scenario as in "Acceptance tests by hand" |
| `sdd regression` | Run the project's test command, then the acceptance tests, then the gates |
| `sdd prove red` / `green` | Run the feature's acceptance tests before the code (they must fail) and after (they must pass, test file unchanged); note both results and the dates in `verification.md` |
| `sdd security` | Apply "Secret check" to the whole repository, then run whichever code analyser and dependency auditor the stack has; report each as clean, findings or NOT RUN |
| `sdd audit` | Apply "Secret check" |
| `sdd pentest` | The person runs Strix themselves; see `Penetration-Testing.md` |

## Setup by hand

1. **Profile.** Read file names and manifests only (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `*.csproj`, `Gemfile`, `composer.json`, CI files). Never open `.env` files, key files or credential files; list them under "Protected paths". Write `.sdd/codebase-profile.md` with: languages, frameworks, package manager, test tools, the build / test / lint commands, top-level folders, CI, protected paths.
2. **Folders.** Create `.sdd/specs/`, `.sdd/extensions/`, `.sdd/adr/`.
3. **Team rules.** Copy `templates/constitution.md` to `.sdd/constitution.md` (status stays `draft`).
4. **Config.** Write `.sdd/config.json`:

```json
{
  "version": 1,
  "specsDir": ".sdd/specs",
  "e2eDir": "tests/e2e",
  "e2eFramework": null,
  "baseUrl": null,
  "commands": { "test": null, "e2e": null },
  "lifecycle": { "constitution": true, "clarify": true, "plan": true, "tasks": true, "tests": true,
                 "e2e": true, "red-first": true, "secrets": true, "code-scan": true, "dependencies": true,
                 "review": true, "pentest": true },
  "skipped": {},
  "project": { "kind": null, "stack": null }
}
```

5. **Agent instructions.** Add a short section to `CLAUDE.md` or `AGENTS.md`: this repository uses spec-driven development; read the profile and team rules first; no feature code without an approved spec; approvals belong to people.
6. **Ignore rules.** Make sure `.gitignore` contains `.env`, `.env.*`, `*.pem`, `*.key` and `strix_runs/`.
7. **Ask the setup questions**, one at a time, recommended answer first: what is being built (empty repository only); the test command; the form of acceptance tests; where the app runs locally; whether to keep every check.

## Which phase is a feature in

Read `.sdd/specs/<feature>/` and take the first line that matches. Skip a line whose check is switched off.

| What you find | Phase | Next action |
|---|---|---|
| No `spec.md` | Specify | Write the spec |
| `Status:` is not `approved`, open `[NEEDS CLARIFICATION` markers | Clarify | Resolve the questions |
| `Status:` is not `approved` | Awaiting approval | A person sets `Status: approved` |
| No `plan.md` | Plan | Write the plan; a person approves |
| No `tasks.md` | Tasks | Write the tasks; a person approves |
| Unchecked `- [ ] T-` lines | Build | Build the next task |
| A requirement no test names | Acceptance tests | Write them |
| No `verification.md` | Verify | Prove each requirement |
| Otherwise | Ship | Readiness report; a person merges |

## The gates

Report each failure with the file and the id. A check the team switched off is not applied; say so in the report.

1. The spec defines at least one requirement, written `- REQ-001: ...`. Ids are unique. No requirement is empty or still contains `…`, `...`, `TBD` or `<placeholder>` once the spec is approved.
2. `plan.md` or `tasks.md` exists only if the spec says `Status: approved` on a line of its own.
3. `tasks.md` exists only if `plan.md` exists. *(check: plan)*
4. No `[NEEDS CLARIFICATION` marker remains once the spec is approved. *(check: clarify)*
5. Every requirement id appears in the `(covers: ...)` of at least one task, every task covers at least one requirement, and no task names an unknown id. *(check: tasks)*
6. Every requirement whose tasks are all checked is named by a real test, in a test file whose path contains the feature name. A placeholder or skipped test does not count; documentation does not count. *(check: tests)*
7. A spec marked `Status: shipped` has every task checked and every requirement tested.
8. No credential appears in `spec.md`, `plan.md`, `tasks.md` or `verification.md`. *(check: secrets)*

## Acceptance tests by hand

For each scenario line `- REQ-001 — Given ..., when ..., then ...` in the spec, write one test in the project's own test framework:

- one test per scenario, in a file whose name contains the feature name, inside the configured `e2eDir`;
- the requirement id in the test's name, tag or marker;
- the Given / When / Then phrases as the test's steps, with selectors kept in one shared helper rather than in each test;
- for stacks without a browser test tool, a Gherkin `.feature` file with each scenario tagged `@REQ-001`;
- a requirement with no scenario is listed as a gap in your report, never given an empty passing test;
- credentials come from environment variables, never from the test file.

## Secret check

Search `.sdd/`, the acceptance-test folder, `CLAUDE.md` and `AGENTS.md` for: private-key headers, long tokens with well-known prefixes, credentials inside URLs, and any name containing `key`, `secret`, `password` or `token` that is assigned a literal value. Report the file and line, never the value. Also confirm that no `.env` or key file is tracked by git and that `.sdd/config.json` holds no credential. If something is found: the person revokes it first, then it is removed.

## What manual mode cannot give you

A machine-checked exit code for CI. Until the tool is added, the gates are as reliable as the agent applying them, so ask a person to spot-check the gate report before anything ships.
