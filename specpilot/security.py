"""Security primitives used by every other module.

Threat model (see wiki/Security-Model.md): SpecPilot runs inside repositories it does not
control, next to an AI agent that may be steered by text in those repositories. So:
  * every path derived from input is confined to the project root, and never written through
    a symlink (path traversal, symlink clobbering);
  * file reads are size-bounded and never touch secret-like files;
  * child processes are started without a shell, with an argument list and a minimal environment;
  * credentials are never accepted as arguments, never written to disk, and are redacted from
    anything we print.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

MAX_READ_BYTES = 1_000_000
FEATURE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# File names whose contents must never be read, printed or copied.
SENSITIVE_NAME = re.compile(
    r"(^|/)(\.env(\..+)?|.*\.pem|.*\.key|.*\.p12|.*\.pfx|.*\.jks|.*\.keystore|.*\.tfvars|"
    r"id_(rsa|dsa|ecdsa|ed25519)[^/]*|\.npmrc|\.pypirc|\.netrc|\.htpasswd|\.git-credentials|"
    r"kubeconfig|.*credentials.*\.json|.*service[_-]?account.*\.json|.*secrets?\.(ya?ml|json|toml))$"
    r"|(^|/)\.aws/credentials$|(^|/)\.docker/config\.json$|(^|/)\.kube/config$",
    re.IGNORECASE,
)
SENSITIVE_OK_SUFFIX = (".example", ".sample", ".template", ".dist", ".pub")

# Token shapes: unambiguous enough to redact from any output as well as to report.
TOKEN_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("API key (sk- style)", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("credentials in a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s:@]{6,}@")),
]
_NOT_A_VALUE = r"(?!\$|<|\{|your|xxx|\*|changeme|example|placeholder|redacted|none\b|null\b|true\b|false\b)"
# Context-dependent: a credential-like name assigned a literal value.
ASSIGNMENT_PATTERNS = [
    (
        "hard-coded credential",
        re.compile(
            r"(?i)(?<![A-Za-z0-9])[\"']?[A-Za-z0-9_.-]*"
            r"(?:api[_-]?key|secret|passw(?:or)?d|passwd|token|private[_-]?key|access[_-]?key)"
            r"[A-Za-z0-9_-]*[\"']?\s*[:=]\s*"
            r"(?:[\"']" + _NOT_A_VALUE + r"[^\"'\s]{12,}[\"']"  # quoted literal
            r"|" + _NOT_A_VALUE + r"(?=[A-Za-z0-9_\-/+=!@#%^*]*\d)[A-Za-z0-9_\-/+=!@#%^*]{16,})"  # bare literal
        ),
    ),
]
SECRET_PATTERNS = TOKEN_PATTERNS + ASSIGNMENT_PATTERNS

# Environment variables whose values are secrets: redacted from output, never logged.
SECRET_ENV = ("LLM_API_KEY", "PERPLEXITY_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")


class SecurityError(Exception):
    """Raised when an operation would cross a security boundary."""


def is_sensitive(rel_path: str) -> bool:
    p = rel_path.replace(os.sep, "/")
    return bool(SENSITIVE_NAME.search(p)) and not p.endswith(SENSITIVE_OK_SUFFIX)


def validate_feature(name: str) -> str:
    """Feature names become directory and file names, so they are strictly kebab-case."""
    if not isinstance(name, str) or not FEATURE_RE.match(name):
        raise SecurityError(
            "feature name must be kebab-case: lowercase letters, digits and hyphens, max 64 chars"
        )
    return name


def safe_join(root: Path, *parts: str) -> Path:
    """Join parts under root and refuse any result that escapes root (after resolving symlinks)."""
    root_r = Path(root).resolve()
    candidate = root_r.joinpath(*parts).resolve()
    if candidate != root_r and root_r not in candidate.parents:
        raise SecurityError(f"path escapes the project root: {'/'.join(parts)}")
    return candidate


def read_text(path: Path, limit: int = MAX_READ_BYTES) -> str | None:
    """Bounded read. Returns None for missing, oversized, non-regular or undecodable files."""
    try:
        p = Path(path)
        if p.is_symlink() or not p.is_file() or p.stat().st_size > limit:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def write_text(root: Path, path: Path, content: str) -> Path:
    """Write inside root only, never through a symlink, creating parents as needed."""
    root_r = Path(root).resolve()
    target = Path(path)
    if not target.is_absolute():
        target = root_r / target
    # Check every existing component between root and target for symlinks.
    rel = os.path.relpath(target, root_r)
    if rel.startswith(".."):
        raise SecurityError(f"refusing to write outside the project root: {path}")
    cur = root_r
    for part in Path(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            raise SecurityError(f"refusing to write through a symlink: {cur}")
    if target.exists():
        if not target.is_file():
            raise SecurityError(f"refusing to overwrite a non-file: {rel}")
        if target.stat().st_nlink > 1:  # a hard link could alias a file outside the project
            raise SecurityError(f"refusing to write through a hard link: {rel}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise SecurityError(f"cannot write {rel}: {exc.strerror or exc}") from exc
    return target


def has_control_chars(text: str) -> bool:
    return any(ch.isspace() or not ch.isprintable() for ch in text)


def one_line(text: str, limit: int = 200) -> str:
    """Collapse to a single printable line. Used before text is embedded in code or instructions."""
    cleaned = "".join(ch if ch.isprintable() else " " for ch in str(text))
    return " ".join(cleaned.split())[:limit]


def redact(text: str, env: dict | None = None) -> str:
    """Remove secret environment values and well-known token shapes from text before printing."""
    env = os.environ if env is None else env
    for name in SECRET_ENV:
        value = env.get(name)
        if value and len(value) >= 6:
            text = text.replace(value, "***REDACTED***")
    for _label, pattern in TOKEN_PATTERNS:
        text = pattern.sub("***REDACTED***", text)
    return text


def scan_text_for_secrets(text: str) -> list[tuple[int, str]]:
    """Return (line_number, kind) for each suspected credential. Never returns the value itself."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append((i, label))
                break
    return hits


def minimal_env(extra_allow: tuple[str, ...] = ()) -> dict:
    """Environment for child processes: only what they need, so unrelated secrets do not leak."""
    allow = {
        "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM", "TMPDIR", "TEMP", "TMP",
        "SYSTEMROOT", "COMSPEC", "PATHEXT", "APPDATA", "LOCALAPPDATA", "USERPROFILE",
        "CI", "VIRTUAL_ENV", "PYTHONPATH", "NO_COLOR", "FORCE_COLOR",
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
    }
    allow.update(extra_allow)
    return {k: v for k, v in os.environ.items() if k in allow or k.upper() in allow}
