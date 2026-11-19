# Changelog

## 2.3.2

### Fixed
- The README, the wiki's Getting Started and the Step-by-Step Workflow described the same process with three different numberings. All three now use one list of eleven steps with identical numbers and names, and a test fails if they drift apart.
- Remaining mentions of the old product name in the reference pages and skills are removed.

## 2.3.1

### Changed
- README rewritten around the real process, step by step: what the person does, what the agent does and what the tool checks at each step, plus a table of what actually runs underneath and how far each security integration has been tested.
- Wiki Getting Started is now a complete worked example from install to ship; the Home and Step-by-Step diagrams show the parallel tracks, red-first proof and the security gate.

## 2.3.0

### Added
- **Security gate** (`sdd security`): four layers, each reported as clean, findings, error or NOT RUN.
  - *Secrets*: the whole working tree and the entire git history. Uses TruffleHog or gitleaks when installed; otherwise a built-in engine with about 55 provider and generic detectors. Findings show kind, location and a fingerprint, never the value. False positives are accepted with `sdd security allow <fingerprint> --reason`, an inline `sdd:allow-secret` marker, or `security.exclude`.
  - *Code scan* and *dependencies*: runs the analysers that fit the detected stack and are installed (semgrep, bandit, gosec, brakeman; osv-scanner, trivy, pip-audit, npm audit, cargo-audit, govulncheck, bundle-audit).
  - `--strict` fails when an enabled layer did not run. `sdd regression` now includes the gate.
- **Parallel delivery**: `parallel-delivery` skill, `/sdd-parallel` command and an `acceptance-tester` subagent that writes acceptance tests from the spec and the plan's new Test contract without reading the implementation.
- **Red-first proof** (`sdd prove red|green <feature>`): records the acceptance tests failing before the code and passing after, and refuses the passing run if the test file changed in between. `sdd verify` checks the record.
- Three new lifecycle checks: `red-first`, `code-scan`, `dependencies`.
- Spec template: a section for security requirements written as abuse cases (`REQ-S01`).
- `sdd next` shows the parallel test-track step when one is available.

### Changed
- `sdd audit` remains the quick self-check of the SDD setup; `sdd security` is the full gate.
- The URL-credential detector no longer flags a variable in the password position.

## 2.2.4

### Fixed
- The directory build's manifest no longer carries web links (author URL, homepage, repository). The directory's scan paired the author link with the Security Model page's discussion of credentials and held the version.

## 2.2.3

### Fixed
- The directory build (`plugin/`) no longer contains any remote web address in its documents, and its test-automation skill no longer describes sign-in details as environment variables. The directory's scan combined those across files into one remaining hold.

## 2.2.2

### Fixed
- The directory build's `security-pentest` skill and Security Model page no longer pair a remote address with wording about reading a key from the environment, which the directory's scan holds for review.
- The directory build (`plugin/`) no longer writes a setting directly in front of a URL (for example a local model endpoint or the app's base address), which the directory's scan reads as a credential being sent to a host.

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
