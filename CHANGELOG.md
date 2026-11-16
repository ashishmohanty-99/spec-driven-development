# Changelog

## 2.2.1

### Fixed
- Every skill, command and subagent description is now a double-quoted YAML string, so a colon or `#` inside it cannot be misread.
- The directory build (`plugin/`) no longer shows test-account variable names or shell lines that set them; it describes them in words.

## 2.2.0

### Changed
- The skill and plugin are now named **spec-driven-development-by-ashish-mohanty**, shown in listings as "Spec Driven Development By Ashish Mohanty". Anyone who installed or uploaded it under the previous name should remove that copy and install this one.
- New icon: a spec sheet with ticked requirements and an approval badge (`tools/make_icon.py` redraws it).

## 2.1.0

### Added
- `plugin/`: a documentation-only build of the skill for plugin directories, which accept only Markdown, JSON, YAML and images from publishers that are not verified organisations. It holds the entry skill, all fifteen phase skills, the commands, the subagents, the templates, the reference pages and an icon, and no scripts. Rebuild with `python tools/build_plugin.py`; CI fails if it is out of date.
- Manual mode (`references/Manual-Mode.md`): every `sdd` command's job described as steps an agent can apply by hand, so the method works where the tool is not installed.

### Changed
- When the tool is unavailable, the skills now fall back to manual mode instead of asking for an install.

## 2.0.1

### Fixed
- The skill bundle now contains exactly one `SKILL.md`, as upload hosts (claude.ai → Customize → Skills) require. The phase skills it installs into projects are stored inside the bundle as `PHASE.md` and written out as `SKILL.md` by `sdd init`.

## 2.0.0

### Changed
- The skill is now named **spec-driven-development-by-ashish-mohanty** (folder `skills/spec-driven-development-by-ashish-mohanty/`). The `sdd` command and the Python package name are unchanged.
- An empty repository now defaults to Gherkin acceptance tests instead of Python.

### Added
- **Guided setup.** `sdd questions` lists only what could not be detected (stack for new projects, test command, acceptance-test form, local address, lifecycle choice); `sdd answer <id> <value>` records each answer. New `guided-setup` skill and `/sdd-setup` command.
- **Choose your lifecycle.** `sdd lifecycle` shows nine optional checks. `sdd lifecycle skip <check> --reason "..."` switches one off, prints what that costs and records the reason; every status, verify, regression and next report repeats which checks are off. Approving a spec before code cannot be switched off.
- **`sdd next`**: the single next action for the repository and for each feature.
- **Language-agnostic acceptance tests.** `sdd gen-tests` now writes Playwright Python, Playwright TypeScript, or Gherkin feature files, chosen from the detected stack.
- **New-project scaffolding.** `project-scaffold` skill, `/sdd-scaffold` command and a Project Structure reference: agree a conventional folder tree, generate it with the ecosystem's tooling, prove build, lint and one test.
- Friendlier `sdd init` output: what was found, what was done, what to do next.

### Fixed
- Documentation files inside a test folder no longer count as tests for traceability.
- A scenario that quotes markup such as `<b>` is no longer mistaken for a template placeholder.

## 1.2.0

### Changed
- The repository is now directly installable as a skill: `npx skills add ashishmohanty-99/spec-driven-development`. The complete skill (entry `SKILL.md`, bundled CLI, reference pages) is committed at `skills/spec-driven-development-by-ashish-mohanty/`, so no release or build step is needed to share it.
- The Python package source moved to `skills/spec-driven-development-by-ashish-mohanty/scripts/specpilot/`; `pip install` and the `sdd` command are unchanged.
- Reference pages moved from `wiki/` to `skills/spec-driven-development-by-ashish-mohanty/references/`; the wiki is published from both.
- `tools/build_skill.py` now only zips the skill folder for upload-only hosts.

## 1.1.0

### Added
- Standalone skill bundle (`python tools/build_skill.py` → `dist/specpilot-skill.zip`) containing the entry skill, the CLI and the reference pages. Attached to tagged releases.
- `sdd init --vendor`: copies the CLI into `.sdd/bin/` so a project and its CI need nothing installed.
- `--dir` is accepted before or after the command.
- `sdd verify`: a spec marked `shipped` must have every task checked and every requirement tested.

### Fixed (from an independent audit)
- `sdd regression` reported a missing or mistyped test command as a skip and passed. It now fails. Relative commands resolve against the project, not the caller's directory.
- Generated placeholder tests no longer count as proof of a requirement.
- A test proves a requirement only for its own feature when several features share an id.
- `sdd init --force` no longer overwrites the constitution, `.sdd/extensions/` or the e2e connector.
- Secret detection covers quoted and prefixed names, credentials in URLs, JWTs, PGP and GitLab tokens; a large repository can no longer push SDD files past the scan limit.
- Directory names can no longer inject text into the codebase profile.
- The pentest record no longer stores instruction text or query strings; the timeout is enforced; only "clean" and "findings" pass through from Strix.
- A malformed or mistyped `.sdd/config.json` is an error instead of silently using defaults; bad input no longer prints tracebacks.
- Feature folders with invalid names fail the gate instead of being skipped.
- `sdd gen-tests` refuses to overwrite a hand-written test file, ignores template placeholder scenarios, and honours a custom `e2eDir`.
- The spec template no longer trips the open-question gate; empty requirements count as placeholders.
- A status line must contain only the status word (`approved-pending-review` is not approved).
- Writes through hard links are refused; more secret file names are protected.
- "and" inside quoted text is no longer treated as a step boundary in e2e scenarios.

### Changed
- Minimum Python version is 3.11.

## 1.0.0
- Python rewrite: `sdd` CLI, 13 skills, 15 commands, security model, wiki.
