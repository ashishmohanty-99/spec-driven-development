# Changelog

## 1.2.0

### Changed
- The repository is now directly installable as a skill: `npx skills add ashishmohanty-99/spec-driven-development`. The complete skill (entry `SKILL.md`, bundled CLI, reference pages) is committed at `skills/specpilot/`, so no release or build step is needed to share it.
- The Python package source moved to `skills/specpilot/scripts/specpilot/`; `pip install` and the `sdd` command are unchanged.
- Reference pages moved from `wiki/` to `skills/specpilot/references/`; the wiki is published from both.
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
