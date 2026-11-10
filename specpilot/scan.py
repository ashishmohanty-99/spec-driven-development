"""Codebase profiler. Reads file names and a fixed list of manifests only. No network access."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .security import is_sensitive, one_line, read_text

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", ".nuxt", "target", "vendor", ".venv",
    "venv", "__pycache__", ".gradle", ".idea", ".vscode", "coverage", ".cache", ".turbo", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "strix_runs",
}
LANGS = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
    ".swift": "Swift", ".scala": "Scala", ".c": "C", ".cpp": "C++", ".sh": "Shell",
}
JS_FRAMEWORKS = ["react", "next", "vue", "nuxt", "svelte", "@angular/core", "express", "fastify",
                 "@nestjs/core", "koa", "hono", "vite", "electron"]
JS_TEST = ["vitest", "jest", "mocha", "@playwright/test", "playwright", "cypress", "ava"]
JS_QUALITY = ["eslint", "prettier", "typescript", "@biomejs/biome"]
PY_FRAMEWORKS = {"django": "Django", "fastapi": "FastAPI", "flask": "Flask",
                 "sqlalchemy": "SQLAlchemy", "pydantic": "Pydantic", "celery": "Celery"}
PY_TEST = {"pytest": "pytest", "playwright": "Playwright", "hypothesis": "Hypothesis", "tox": "tox"}
PY_QUALITY = {"ruff": "ruff", "mypy": "mypy", "black": "black", "bandit": "bandit",
              "pip-audit": "pip-audit", "flake8": "flake8"}
TEST_FILE = re.compile(
    r"(\.(test|spec)\.[jt]sx?$|(^|/)test_[^/]+\.py$|_test\.(go|py)$|Test\.java$|_spec\.rb$|"
    r"(^|/)tests?/|(^|/)__tests__/)"
)
HUMAN_HEADING = "## Human-supplied context (preserved across re-scans)"
MAX_FILES = 5000
MAX_DEPTH = 6


def walk(root: Path) -> list[str]:
    """Bounded walk returning repo-relative POSIX paths. Never follows symlinks."""
    root = Path(root)
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = os.path.relpath(dirpath, root)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and depth < MAX_DEPTH and not os.path.islink(os.path.join(dirpath, d))
        )
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            rel = name if rel_dir == "." else f"{rel_dir}/{name}".replace(os.sep, "/")
            files.append(rel)
            if len(files) >= MAX_FILES:
                return files
    return files


def _json(path: Path) -> dict:
    text = read_text(path)
    if text is None:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def scan(root: Path) -> dict:
    root = Path(root).resolve()
    files = walk(root)
    fileset = set(files)
    has = fileset.__contains__
    p: dict = {
        "name": one_line(root.name, 80) or "project", "fileCount": len(files), "languages": [],
        "frameworks": [], "testTools": [], "qualityTools": [], "packageManagers": [],
        "commands": {}, "ci": [], "docs": [], "topDirs": [], "monorepo": None,
        "testFileCount": 0, "sensitiveFiles": [], "agentFiles": [], "notes": [],
    }
    cmds: dict = p["commands"]

    counts: dict = {}
    for f in files:
        lang = LANGS.get(os.path.splitext(f)[1])
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    p["languages"] = [{"name": k, "files": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
    p["topDirs"] = sorted({f.split("/")[0] for f in files if "/" in f})

    # Python
    py_text = "\n".join(
        t for t in (read_text(root / n) for n in
                    ("pyproject.toml", "requirements.txt", "requirements-dev.txt", "setup.cfg", "Pipfile"))
        if t
    ).lower()
    if py_text or has("setup.py"):
        p["packageManagers"].append(
            "poetry" if has("poetry.lock") else "uv" if has("uv.lock") else "pipenv" if has("Pipfile") else "pip"
        )
        for table, dest in ((PY_FRAMEWORKS, "frameworks"), (PY_TEST, "testTools"), (PY_QUALITY, "qualityTools")):
            for key, label in table.items():
                if re.search(rf"(^|[^a-z0-9_-]){re.escape(key)}([^a-z0-9_-]|$)", py_text):
                    p[dest].append(label)
        if "pytest" in p["testTools"]:
            cmds.setdefault("test", "pytest")
        if "ruff" in p["qualityTools"]:
            cmds.setdefault("lint", "ruff check .")
        if "mypy" in p["qualityTools"]:
            cmds.setdefault("typecheck", "mypy .")

    # JavaScript / TypeScript
    pkg = _json(root / "package.json")
    if pkg:
        deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
        p["frameworks"] += [d for d in JS_FRAMEWORKS if d in deps]
        p["testTools"] += [d for d in JS_TEST if d in deps]
        p["qualityTools"] += [d for d in JS_QUALITY if d in deps]
        pm = "pnpm" if has("pnpm-lock.yaml") else "yarn" if has("yarn.lock") else \
            "bun" if has("bun.lockb") or has("bun.lock") else "npm"
        p["packageManagers"].append(pm)
        scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
        # Only the script *name* is used; script bodies are never copied into agent instructions.
        for key in ("dev", "start", "build", "test", "lint", "typecheck", "format"):
            if key in scripts:
                cmds.setdefault(key, "npm test" if (key == "test" and pm == "npm")
                                else f"{'npm run' if pm == 'npm' else pm} {key}")
        if pkg.get("workspaces"):
            p["monorepo"] = "npm/yarn workspaces"
    for fname, label in (("pnpm-workspace.yaml", "pnpm workspaces"), ("lerna.json", "lerna"),
                         ("nx.json", "nx"), ("turbo.json", "turborepo"), ("go.work", "go workspace")):
        if has(fname):
            p["monorepo"] = label

    # Other ecosystems
    eco = [
        ("go.mod", "go modules", {"test": "go test ./...", "build": "go build ./...", "lint": "go vet ./..."}),
        ("Cargo.toml", "cargo", {"test": "cargo test", "build": "cargo build", "lint": "cargo clippy"}),
        ("pom.xml", "maven", {"test": "mvn test", "build": "mvn package"}),
        ("Gemfile", "bundler", {"test": "bundle exec rspec"}),
        ("composer.json", "composer", {}),
    ]
    for fname, label, defaults in eco:
        if has(fname):
            p["packageManagers"].append(label)
            for k, v in defaults.items():
                cmds.setdefault(k, v)
    if has("build.gradle") or has("build.gradle.kts"):
        p["packageManagers"].append("gradle")
        gradle = "./gradlew" if has("gradlew") else "gradle"
        cmds.setdefault("test", f"{gradle} test")
        cmds.setdefault("build", f"{gradle} build")
    if any(f.endswith((".csproj", ".sln")) for f in files):
        p["packageManagers"].append("dotnet")
        cmds.setdefault("test", "dotnet test")
        cmds.setdefault("build", "dotnet build")

    makefile = read_text(root / "Makefile")
    if makefile:
        targets = set(re.findall(r"^([a-zA-Z][\w-]*):", makefile, flags=re.MULTILINE))
        for t in ("test", "build", "lint", "dev", "check"):
            if t in targets:
                cmds.setdefault(t, f"make {t}")

    if any(f.startswith(".github/workflows/") for f in files):
        p["ci"].append("GitHub Actions")
    for fname, label in ((".gitlab-ci.yml", "GitLab CI"), ("Jenkinsfile", "Jenkins"),
                         ("azure-pipelines.yml", "Azure Pipelines"), (".circleci/config.yml", "CircleCI"),
                         ("bitbucket-pipelines.yml", "Bitbucket Pipelines")):
        if has(fname):
            p["ci"].append(label)

    p["docs"] = [f for f in ("README.md", "CONTRIBUTING.md", "ARCHITECTURE.md", "SECURITY.md", "CHANGELOG.md") if has(f)]
    if any(re.match(r"^docs?/", f) for f in files):
        p["docs"].append("docs/")
    if any(re.search(r"(^|/)(adr|adrs|decisions)/", f, re.IGNORECASE) for f in files):
        p["docs"].append("ADR directory")
    p["agentFiles"] = [f for f in ("AGENTS.md", "CLAUDE.md", ".cursorrules", ".github/copilot-instructions.md", "GEMINI.md") if has(f)]

    p["testFileCount"] = sum(1 for f in files if TEST_FILE.search(f) and not f.startswith(".sdd/"))
    p["sensitiveFiles"] = [one_line(f, 200) for f in files if is_sensitive(f)]

    for key in ("frameworks", "testTools", "qualityTools", "packageManagers", "ci", "docs"):
        p[key] = list(dict.fromkeys(p[key]))

    gitignore = read_text(root / ".gitignore") or ""
    if p["sensitiveFiles"] and not re.search(r"^\s*\.env", gitignore, flags=re.MULTILINE) and any(
        f.split("/")[-1].startswith(".env") for f in p["sensitiveFiles"]
    ):
        p["notes"].append("SECURITY: a .env file exists but .gitignore has no .env rule. Add one before committing.")
    if not p["testFileCount"]:
        p["notes"].append("No test files detected: the first feature must introduce test infrastructure.")
    if not p["ci"]:
        p["notes"].append("No CI detected: gates run only locally until CI is added.")
    if not p["agentFiles"]:
        p["notes"].append("No agent instruction file found (AGENTS.md / CLAUDE.md).")
    return p


def render_profile(p: dict, previous: str | None = None) -> str:
    def lst(items):
        return ", ".join(items) if items else "_none detected_"

    cmds = "\n".join(f"| {k} | `{v}` |" for k, v in p["commands"].items()) or \
        "| _none detected_ | Confirm with the team and fill in |"
    langs = ", ".join(f"{l['name']} ({l['files']})" for l in p["languages"]) or "_none detected_"
    protected = "\n".join(f"- `{f}`" for f in p["sensitiveFiles"]) or "_No secret-like files detected._"
    notes = "\n".join(f"- {n}" for n in p["notes"]) or "- None."
    fresh = f"""# Codebase Profile: {p['name']}

> Generated by `sdd scan` from file names and manifests only. Nothing here was read from secret files.
> Items marked **CONFIRM** are inferences. A human verifies them before the constitution is ratified.
> Only the "Human-supplied context" section at the bottom is preserved across re-scans.

## Stack
- **Languages (by file count):** {langs}
- **Frameworks / libraries:** {lst(p['frameworks'])}
- **Package managers:** {lst(p['packageManagers'])}
- **Test tools:** {lst(p['testTools'])}
- **Quality and security tools:** {lst(p['qualityTools'])}
- **Monorepo:** {p['monorepo'] or 'no'}
- **CI:** {lst(p['ci'])}

## Commands (CONFIRM)
| Purpose | Command |
|---|---|
{cmds}

## Layout
- **Top-level directories:** {lst(p['topDirs'])}
- **Files scanned:** {p['fileCount']}; **test files:** {p['testFileCount']}
- **Docs present:** {lst(p['docs'])}
- **Agent instruction files:** {lst(p['agentFiles'])}

## Protected paths (agents must not read, print or edit)
{protected}

## Observations
{notes}

{HUMAN_HEADING}
<!-- Add: domain glossary, architectural invariants, ownership, things the scan cannot see. -->
"""
    if previous and HUMAN_HEADING in previous:
        return fresh[: fresh.index(HUMAN_HEADING)] + previous[previous.index(HUMAN_HEADING):]
    return fresh
