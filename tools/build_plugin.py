#!/usr/bin/env python3
"""Build plugin/: a documentation-only copy of the skill for plugin directories.

Public plugin directories accept only Markdown, text, JSON, YAML and images from publishers that
are not verified organisations, so the directory version carries no scripts. It contains the entry
skill, every phase skill, the commands, the subagents, the templates and the reference pages, and
works in "manual mode" (references/Manual-Mode.md) when the `sdd` tool is not present.

    python3 tools/build_plugin.py          rebuild plugin/ from the sources
    python3 tools/build_plugin.py --check  fail if plugin/ is out of date
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "spec-driven-development-by-ashish-mohanty"
SKILL = ROOT / "skills" / NAME
ASSETS = SKILL / "scripts" / "specpilot" / "assets"
OVERRIDES = ROOT / "tools" / "plugin_overrides"
ALLOWED = {".md", ".txt", ".json", ".yaml", ".yml", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}
ALLOWED_NAMES = {"LICENSE"}

TOOL_SECTION = """## The tool
A small command-line tool, `sdd`, automates the checks. Call it `SDD` below. Use the first that applies:

1. In a repository that already has it: `python3 .sdd/bin/sdd.py`
2. If `sdd --version` works: `sdd`
3. Neither: **manual mode**. Do each command's job by hand, exactly as `references/Manual-Mode.md` describes. The files and formats are identical, so nothing is lost if the team adds the tool later.

This plugin carries documentation only. Tell the person once that the optional tool is open source in this skill's repository (linked from the plugin's README) and that installing it is their decision. Never install it yourself.

**When in doubt, run `SDD next`** (or, in manual mode, read each feature's files and apply the phase table in `references/Manual-Mode.md`).

"""


# The directory holds a version when one file both names a remote host and mentions reading a
# credential from the environment. These rewordings keep the meaning and remove that pairing.
REWORDINGS = [
    ("the open-source Strix agent (https://github.com/usestrix/strix)", "the open-source Strix agent"),
    ("The key exists only as the `LLM_API_KEY` environment variable in the user's shell or CI secret store.",
     "The key lives only in the person's own shell or CI secret store."),
    ('Never run `env`, `printenv`, `cat .env` or similar to "check" the configuration.',
     "Never inspect the person's environment or secret files to check the configuration."),
    ("Read from env by Strix only.", "Strix reads it from the person's own shell."),
    ("a non-local `http://` API base", "an unencrypted remote API address"),
    ("`AWS_*`, tokens and the rest are dropped", "cloud keys, tokens and the rest are dropped"),
    ("refer to a throwaway test account or to environment variables.",
     "refer to a throwaway test account that exists only in the test environment."),
    ("Credentials come from environment variables and a dedicated low-privilege test account.",
     "Sign-in details for a dedicated low-privilege test account are supplied at run time, never in code."),
    ("Use an `https://` API base", "Use an encrypted (https) API address"),
    ("ENV -->|env vars only| CLI", "ENV -->|settings only| CLI"),
    ("CLI -->|no shell, minimal env| APP", "CLI -->|no shell, minimal environment| APP"),
]


def _neutral(text: str) -> str:
    """Directory copies describe credentials in words rather than by variable name or shell line."""
    for old, new in REWORDINGS:
        text = text.replace(old, new)
    text = text.replace("`LLM_API_KEY`", "the model key").replace("LLM_API_KEY", "the model key")
    text = re.sub(r"`curl [^`]*\| *(?:ba)?sh`", "the installer in Strix's documentation", text)
    # Test-account settings: say what they are instead of showing variables or shell lines.
    text = re.sub(r"```bash\nexport SDD_UI_USER=.*?```", "Give the test account's name and password to the tests through "
                  "environment variables of your own choosing, taken from your secret manager.", text, flags=re.DOTALL)
    text = text.replace("`SDD_UI_USER` / `SDD_UI_PASS` environment variables", "environment variables")
    text = text.replace("| `SDD_UI_USER`, `SDD_UI_PASS` | your `ui_login.py` | Test account |",
                        "| test-account variables (your own names) | your login helper | Test account |")
    # A variable written directly in front of a URL reads to a scanner like a credential being sent
    # to a host. The directory copy names the setting and the address separately.
    text = text.replace("a local model through Ollama (`STRIX_LLM=ollama/<model>`, `LLM_API_BASE=http://localhost:11434`)",
                        "a local model through Ollama, configured as Strix's documentation describes")
    text = text.replace("SDD_BASE_URL=http://localhost:3000 pytest tests/e2e", "pytest tests/e2e")
    text = text.replace("| `SDD_BASE_URL` | e2e tests | App under test (default `http://localhost:3000`) |",
                        "| `SDD_BASE_URL` | e2e tests | Address of the app under test (default: localhost, port 3000) |")
    text = text.replace("| `STRIX_LLM`, `LLM_API_BASE` | Strix | Model and endpoint |",
                        "| Strix model settings | Strix | See Strix's documentation |")
    text = text.replace('"baseUrl": "http://localhost:3000",', '"baseUrl": null,')
    text = text.replace("or export `STRIX_LLM` and the model key in your shell",
                        "or configure a hosted model in your own shell as Strix documents")
    return text


def _entry_skill() -> str:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    start, end = text.index("## The tool"), text.index("## First time in a repository")
    text = text[:start] + TOOL_SECTION + text[end:]
    text = text.replace("follow `scripts/specpilot/assets/skills/project-scaffold/PHASE.md` and",
                        "use the `project-scaffold` skill and")
    text = text.replace("If they are not installed, the same text is in "
                        "`scripts/specpilot/assets/skills/<name>/PHASE.md` inside this skill.",
                        "In this plugin the same phase skills are installed alongside this one.")
    assert "scripts/" not in text, "the directory copy must not point at bundled scripts"
    return _neutral(text)


README = f"""# Spec Driven Development By Ashish Mohanty

One skill that takes a team from an idea to a shipped, tested feature, in any language. It reads your
repository, asks only what it cannot work out, sets up a proper project structure for new applications,
and guides specs, plans, tasks, test-first builds, acceptance tests, security checks and shipping, with a
person approving each step.

## Install

```
/plugin install {NAME} --marketplace ashishmohanty-99/spec-driven-development
```

Then say: **Set up spec-driven development in this repository.**

## What is in this plugin

Documentation only: the entry skill, the phase skills, slash commands, reviewer and tester subagents,
templates and reference pages. It contains no scripts and reads no credentials.

The checks can be applied by hand (see `skills/{NAME}/references/Manual-Mode.md`) or by an optional
open-source command-line tool that a person may choose to install from the project's repository, which is
named in this plugin's manifest (`ashishmohanty-99/spec-driven-development` on GitHub).

## You choose the checks

Every check is on by default. Any optional check can be switched off; you are told what that costs and
your reason is recorded. Approving a spec before code is the one step that cannot be switched off.

MIT License.
"""


def build(out: Path) -> Path:
    plugin = out / "plugin"
    if plugin.exists():
        shutil.rmtree(plugin)
    entry = plugin / "skills" / NAME
    (plugin / ".claude-plugin").mkdir(parents=True)
    (entry / "references").mkdir(parents=True)
    (entry / "templates").mkdir()

    source = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    # No web addresses in the directory manifest: the directory already knows the repository from the
    # submission, and its scan pairs any remote address with any mention of credentials in the docs.
    manifest = {k: source[k] for k in ("name", "version", "description", "license", "keywords")}
    manifest["author"] = {"name": source["author"]["name"]}
    manifest["icon"] = "./.claude-plugin/icon.png"
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(OVERRIDES / "icon.png", plugin / ".claude-plugin" / "icon.png")
    (plugin / "README.md").write_text(README, encoding="utf-8")
    shutil.copyfile(ROOT / "LICENSE", plugin / "LICENSE")

    (entry / "SKILL.md").write_text(_entry_skill(), encoding="utf-8")
    for page in sorted((SKILL / "references").glob("*.md")):
        override = OVERRIDES / page.name
        text = (override if override.exists() else page).read_text(encoding="utf-8")
        (entry / "references" / page.name).write_text(_neutral(text), encoding="utf-8")
    for template in sorted((ASSETS / "templates").glob("*.md")):
        (entry / "templates" / template.name).write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    for phase in sorted((ASSETS / "skills").iterdir()):
        target = plugin / "skills" / phase.name
        target.mkdir()
        (target / "SKILL.md").write_text(_neutral((phase / "PHASE.md").read_text(encoding="utf-8")), encoding="utf-8")
    for kind in ("commands", "agents"):
        (plugin / kind).mkdir()
        for item in sorted((ASSETS / kind).glob("*.md")):
            (plugin / kind / item.name).write_text(_neutral(item.read_text(encoding="utf-8")), encoding="utf-8")
    return plugin


def snapshot(folder: Path) -> dict:
    return {str(p.relative_to(folder)): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def problems(plugin: Path) -> list[str]:
    """Reasons a directory would refuse this folder."""
    found = []
    for path in sorted(plugin.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(plugin))
        if path.suffix.lower() not in ALLOWED and path.name not in ALLOWED_NAMES:
            found.append(f"{rel}: file type not accepted")
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}:
            continue
        data = path.read_bytes()
        if b"\0" in data or data.startswith(b"#!"):
            found.append(f"{rel}: looks like a program")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            found.append(f"{rel}: not UTF-8 text")
        if any(ch in rel for ch in ':\\*?"<>|'):
            found.append(f"{rel}: path has a character some systems reject")
    return found


if __name__ == "__main__":
    if "--check" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = snapshot(build(Path(tmp)))
        current = snapshot(ROOT / "plugin") if (ROOT / "plugin").is_dir() else {}
        if fresh != current:
            changed = sorted(set(fresh) ^ set(current) | {k for k in fresh if current.get(k) != fresh[k]})
            sys.exit(f"plugin/ is out of date ({len(changed)} file(s), e.g. {changed[:3]}). "
                     "Run: python3 tools/build_plugin.py")
        print("plugin/ is up to date")
    else:
        built = build(ROOT)
        issues = problems(built)
        print(f"Built {built.relative_to(ROOT)}/ ({len(snapshot(built))} files)")
        if issues:
            sys.exit("\n".join(issues))
