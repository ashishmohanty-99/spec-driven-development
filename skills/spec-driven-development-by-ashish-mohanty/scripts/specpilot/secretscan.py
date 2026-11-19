"""Secret scanning: the whole working tree and the whole git history.

Two engines, same report:

  * If TruffleHog or gitleaks is installed, it is run and its findings are reported. That is the
    only honest way to be "as good as TruffleHog": use it.
  * Otherwise the built-in engine runs: provider-specific detectors over every text file git knows
    about and over every line ever added in history. It has fewer detectors than TruffleHog and it
    never contacts a provider, so it cannot tell whether a key is still live.

A finding is reported as kind, location and fingerprint. The secret's value is never printed or stored.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from .scan import SKIP_DIRS, walk
from .security import (
    MAX_READ_BYTES,
    SECRET_PATTERNS,
    SecurityError,
    is_sensitive,
    minimal_env,
    one_line,
    read_text,
    write_text,
)

# Provider-specific token shapes, in addition to the core patterns in security.py.
PROVIDER_PATTERNS = [
    ("Anthropic API key", r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    ("OpenAI API key", r"\bsk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,}\b"),
    ("Stripe secret key", r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    ("Stripe webhook secret", r"\bwhsec_[A-Za-z0-9]{24,}\b"),
    ("AWS secret access key", r"(?i)aws_?secret_?access_?key[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{40}\b"),
    ("AWS session/temporary key", r"\bASIA[0-9A-Z]{16}\b"),
    ("Google OAuth client secret", r"\bGOCSPX-[A-Za-z0-9_-]{20,}\b"),
    ("Google service account key", r"\"private_key_id\"\s*:\s*\"[a-f0-9]{40}\""),
    ("Azure storage account key", r"(?i)AccountKey=[A-Za-z0-9+/=]{60,}"),
    ("Azure AD client secret", r"\b[A-Za-z0-9_~.-]{3}8Q~[A-Za-z0-9_~.-]{30,}\b"),
    ("Slack webhook", r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]{20,}"),
    ("Discord webhook", r"https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]{30,}"),
    ("Discord bot token", r"\b[MN][A-Za-z0-9_-]{23,25}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,}\b"),
    ("Telegram bot token", r"\b\d{8,10}:AA[A-Za-z0-9_-]{33}\b"),
    ("Twilio API key", r"\bSK[0-9a-f]{32}\b"),
    ("SendGrid API key", r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}\b"),
    ("Mailgun API key", r"\bkey-[0-9a-f]{32}\b"),
    ("Mailchimp API key", r"\b[0-9a-f]{32}-us\d{1,2}\b"),
    ("npm access token", r"\bnpm_[A-Za-z0-9]{36}\b"),
    ("PyPI upload token", r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{50,}\b"),
    ("RubyGems API key", r"\brubygems_[0-9a-f]{48}\b"),
    ("Docker Hub token", r"\bdckr_pat_[A-Za-z0-9_-]{27,}\b"),
    ("GitHub fine-grained token", r"\bgithub_pat_[A-Za-z0-9_]{60,}\b"),
    ("GitHub App private key id", r"\bghs_[A-Za-z0-9]{36,}\b"),
    ("Hugging Face token", r"\bhf_[A-Za-z0-9]{34,}\b"),
    ("DigitalOcean token", r"\bdo[por]_v1_[a-f0-9]{64}\b"),
    ("Shopify access token", r"\bshp(?:at|ca|pa|ss)_[a-fA-F0-9]{32}\b"),
    ("Square access token", r"\b(?:EAAA|sq0atp-|sq0csp-)[A-Za-z0-9_-]{22,}\b"),
    ("Databricks token", r"\bdapi[a-f0-9]{32}\b"),
    ("Heroku API key", r"(?i)heroku[a-z_-]*[\"']?\s*[:=]\s*[\"']?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
    ("Linear API key", r"\blin_api_[A-Za-z0-9]{40}\b"),
    ("Notion token", r"\b(?:secret|ntn)_[A-Za-z0-9]{43,}\b"),
    ("Postman API key", r"\bPMAK-[0-9a-f]{24}-[0-9a-f]{34}\b"),
    ("Sentry token", r"\bsntry[su]_[A-Za-z0-9+/=_-]{40,}\b"),
    ("Doppler token", r"\bdp\.(?:pt|st|ct|sa|scim|audit)\.[A-Za-z0-9]{40,}\b"),
    ("Terraform Cloud token", r"\b[A-Za-z0-9]{14}\.atlasv1\.[A-Za-z0-9_-]{60,}\b"),
    ("HashiCorp Vault token", r"\bhv[sb]\.[A-Za-z0-9_-]{24,}\b"),
    ("New Relic key", r"\bNRAK-[A-Z0-9]{27}\b"),
    ("Grafana token", r"\bgl(?:c|sa)_[A-Za-z0-9_=]{32,}\b"),
    ("PlanetScale token", r"\bpscale_(?:tkn|pw|oauth)_[A-Za-z0-9_.-]{32,}\b"),
    ("Supabase service key", r"\bsbp_[a-f0-9]{40}\b"),
    ("age secret key", r"\bAGE-SECRET-KEY-1[0-9A-Z]{58}\b"),
    ("SSH private key (PuTTY)", r"PuTTY-User-Key-File-\d"),
    ("Basic auth header", r"(?i)authorization[\"']?\s*[:=]\s*[\"']?basic\s+[A-Za-z0-9+/=]{16,}"),
    ("Bearer token in header", r"(?i)authorization[\"']?\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
]
# Provider rules come first so the same text is reported under its most specific name.
DETECTORS = [(label, re.compile(pattern)) for label, pattern in PROVIDER_PATTERNS] + list(SECRET_PATTERNS)
# Cheap pre-filter so most lines never reach the detectors.
HINT = re.compile(
    r"(?i)key|secret|token|passw|bearer|basic |BEGIN |AKIA|ASIA|://[^/\s:@]+:[^/\s@]+@|eyJ|xox|gh[pousr]_|github_pat_|"
    r"glpat|sk-|[sr]k_(live|test)_|whsec_|GOCSPX|AIza|hooks\.slack|webhooks/|SG\.|npm_|pypi-|dckr_pat|hf_|shp[a-z]{2}_|"
    r"sq0|EAAA|dapi|lin_api|PMAK|sntry|dp\.|atlasv1|hv[sb]\.|NRAK|gl(c|sa)_|pscale_|sbp_|AGE-SECRET|PuTTY|\d{8,10}:AA|"
    r"[0-9a-f]{32}-us\d|8Q~|rubygems_|do[por]_v1_|ntn_")
SKIP_NAMES = re.compile(r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|Cargo\.lock|go\.sum|"
                        r"composer\.lock|Gemfile\.lock|.*\.min\.(js|css)|.*\.map|.*\.svg)$")
BINARY_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".tgz", ".jar", ".war", ".exe",
                 ".dll", ".so", ".dylib", ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".wasm", ".pyc", ".class", ".bin"}
PRAGMA = "sdd:allow-secret"  # put on a line that holds a known fake value (test fixture, documentation)
MAX_LINE = 4000


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:16]


def scan_line(line: str) -> list[tuple[str, str]]:
    """(kind, fingerprint) for each credential on one line. The value itself is never returned."""
    if len(line) > MAX_LINE or PRAGMA in line or not HINT.search(line):
        return []
    found, seen = [], set()
    for label, pattern in DETECTORS:
        for match in pattern.finditer(line):
            fp = fingerprint(match.group(0))
            if fp not in seen:
                seen.add(fp)
                found.append((label, fp))
    # Keep the most specific name when a generic rule and a provider rule hit the same text.
    if len(found) > 1:
        specific = [f for f in found if f[0] != "hard-coded credential"]
        found = specific or found
    return found


def _skip(rel: str) -> bool:
    parts = rel.split("/")
    return (any(p in SKIP_DIRS for p in parts) or bool(SKIP_NAMES.search(rel))
            or Path(rel).suffix.lower() in BINARY_SUFFIX or rel.startswith(".sdd/bin/"))


def _git(root: Path, *args: str, timeout: int = 180) -> subprocess.CompletedProcess | None:
    git = shutil.which("git")
    if not git or not (Path(root) / ".git").exists():
        return None
    try:
        # No hooks, external diff drivers or text converters: a hostile repository must not run code here.
        return subprocess.run([git, "-c", "core.fsmonitor=false", "-c", "diff.external=", *args], cwd=root,
                              shell=False, capture_output=True, timeout=timeout, check=False, env=minimal_env())
    except (OSError, subprocess.TimeoutExpired):
        return None


def worktree_files(root: Path) -> list[str]:
    """Every file git tracks plus untracked files it does not ignore. Falls back to a plain walk."""
    out = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if out is not None and out.returncode == 0:
        names = [n for n in out.stdout.decode("utf-8", "replace").split("\0") if n]
        return sorted(dict.fromkeys(names))
    return walk(root)


def scan_worktree(root: Path, exclude: tuple[str, ...] = ()) -> list[dict]:
    root = Path(root).resolve()
    findings = []
    for rel in worktree_files(root):
        if _skip(rel) or any(rel.startswith(prefix) for prefix in exclude):
            continue
        if is_sensitive(rel):
            continue  # never opened; a tracked secret file is reported by the caller
        path = root / rel
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_READ_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue
        for number, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            for kind, fp in scan_line(line):
                findings.append({"kind": kind, "file": rel, "line": number, "fingerprint": fp, "where": "working tree"})
    return findings


def scan_history(root: Path, exclude: tuple[str, ...] = (), max_commits: int = 20000) -> dict:
    """Scan every line ever added, on every branch. Returns {findings, commits, scanned, note}."""
    root = Path(root).resolve()
    out = _git(root, "log", "--all", "-p", "--no-color", "--no-ext-diff", "--no-textconv", "-U0",
               f"--max-count={max_commits}", "--format=%x01%H", timeout=300)
    if out is None:
        return {"findings": [], "commits": 0, "scanned": False, "note": "not a git repository, or git unavailable"}
    if out.returncode != 0:
        return {"findings": [], "commits": 0, "scanned": False, "note": "git log failed"}
    findings, seen, commits = [], set(), 0
    commit = path = None
    skip_file = False
    line_no = 0
    for raw in out.stdout.decode("utf-8", "replace").split("\n"):
        if raw.startswith("\x01"):
            commit, commits = raw[1:13], commits + 1
            continue
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
            skip_file = path is None or _skip(path) or any(path.startswith(p) for p in exclude)
            if path and is_sensitive(path) and ("file", path) not in seen:
                seen.add(("file", path))
                findings.append({"kind": "secret-like file committed", "file": path, "line": 0,
                                 "fingerprint": fingerprint("file:" + path), "where": f"history {commit}"})
                skip_file = True
            elif path and is_sensitive(path):
                skip_file = True
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) - 1 if m else 0
            continue
        if not raw.startswith("+") or skip_file:
            continue
        line_no += 1
        for kind, fp in scan_line(raw[1:]):
            if fp not in seen:  # report each distinct secret once, at the newest commit that added it
                seen.add(fp)
                findings.append({"kind": kind, "file": path, "line": line_no, "fingerprint": fp,
                                 "where": f"history {commit}"})
    note = f"history limited to the newest {max_commits} commits" if commits >= max_commits else None
    return {"findings": findings, "commits": commits, "scanned": True, "note": note}


# ── accepted findings ────────────────────────────────────────────────────────────────────────

def _allow_path(root: Path) -> Path:
    return Path(root) / ".sdd" / "security" / "allow.json"


def load_allow(root: Path) -> dict:
    try:
        data = json.loads(read_text(_allow_path(root)) or "{}")
    except ValueError as exc:
        raise SecurityError(f".sdd/security/allow.json is not valid JSON: {exc}") from exc
    return data if isinstance(data, dict) else {}


def allow(root: Path, fp: str, reason: str) -> None:
    """Accept one finding as a false positive. Recorded with a reason, committed, visible in review."""
    if not re.fullmatch(r"[0-9a-f]{16}", fp or ""):
        raise SecurityError("give the 16-character fingerprint printed beside the finding")
    reason = one_line(reason or "", 200)
    if len(reason) < 5:
        raise SecurityError('accepting a finding needs a reason a teammate can read later: --reason "..."')
    data = load_allow(root)
    data[fp] = {"reason": reason, "date": _dt.datetime.now(_dt.UTC).date().isoformat()}
    write_text(root, _allow_path(root), json.dumps(data, indent=2, sort_keys=True) + "\n")


# ── external engines ─────────────────────────────────────────────────────────────────────────

def _run(argv: list[str], root: Path, timeout: int) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(argv, cwd=root, shell=False, capture_output=True, text=True, errors="replace",
                              timeout=timeout, check=False, env=minimal_env())
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_trufflehog(root: Path, verify_live: bool, history: bool, timeout: int = 1800) -> dict | None:
    """Run TruffleHog if installed. Returns None when it is not available."""
    exe = shutil.which("trufflehog")
    if not exe:
        return None
    root = Path(root).resolve()
    in_git = (root / ".git").exists()
    source = ["git", f"file://{root}"] if (in_git and history) else ["filesystem", str(root)]
    argv = [exe, *source, "--json", "--no-update"]
    if not verify_live:
        argv.append("--no-verification")  # by default nothing found is sent anywhere
    out = _run(argv, root, timeout)
    if out is None:
        return {"engine": "trufflehog", "ok": False, "findings": [], "note": "TruffleHog did not finish"}
    findings = []
    for line in out.stdout.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if not isinstance(item, dict) or "DetectorName" not in item:
            continue
        meta = (item.get("SourceMetadata") or {}).get("Data") or {}
        loc = meta.get("Git") or meta.get("Filesystem") or {}
        raw = str(item.get("Raw") or item.get("RawV2") or item.get("Redacted") or "")
        where = f"history {str(loc.get('commit', ''))[:12]}" if loc.get("commit") else "working tree"
        findings.append({"kind": one_line(str(item["DetectorName"]), 60) + (" (LIVE)" if item.get("Verified") else ""),
                         "file": one_line(str(loc.get("file", "?")), 200), "line": int(loc.get("line") or 0),
                         "fingerprint": fingerprint(raw), "where": where, "verified": bool(item.get("Verified"))})
    failed = out.returncode not in (0, 183) and not findings
    return {"engine": "trufflehog", "ok": not failed, "findings": findings,
            "note": "TruffleHog exited with an error" if failed else
                    ("live verification on" if verify_live else "live verification off (add --verify-live)")}


def run_gitleaks(root: Path, history: bool, timeout: int = 1800) -> dict | None:
    """Run gitleaks if installed. Returns None when it is not available."""
    exe = shutil.which("gitleaks")
    if not exe:
        return None
    root = Path(root).resolve()
    report = root / ".sdd" / "security" / "gitleaks-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    mode = ["detect"] if (history and (root / ".git").exists()) else ["detect", "--no-git"]
    out = _run([exe, *mode, "--source", str(root), "--redact", "--no-banner", "--report-format", "json",
                "--report-path", str(report), "--exit-code", "2"], root, timeout)
    try:
        items = json.loads(read_text(report) or "[]")
    except ValueError:
        items = []
    finally:
        report.unlink(missing_ok=True)  # the report can describe secrets; never leave it on disk
    if out is None:
        return {"engine": "gitleaks", "ok": False, "findings": [], "note": "gitleaks did not finish"}
    findings = [{"kind": one_line(str(i.get("RuleID", "secret")), 60), "file": one_line(str(i.get("File", "?")), 200),
                 "line": int(i.get("StartLine") or 0), "fingerprint": fingerprint(str(i.get("Fingerprint", i))),
                 "where": f"history {str(i.get('Commit', ''))[:12]}" if i.get("Commit") else "working tree"}
                for i in items if isinstance(i, dict)]
    failed = out.returncode not in (0, 2) and not findings
    return {"engine": "gitleaks", "ok": not failed, "findings": findings,
            "note": "gitleaks exited with an error" if failed else None}


def scan_secrets(root: Path, history: bool = True, verify_live: bool = False, exclude: tuple[str, ...] = (),
                 engine: str = "auto") -> dict:
    """Full secret scan. Returns {engine, status, findings, accepted, notes}; status is clean|findings|error."""
    root = Path(root).resolve()
    notes: list[str] = []
    result = None
    if engine in ("auto", "trufflehog"):
        result = run_trufflehog(root, verify_live, history)
    if result is None and engine in ("auto", "gitleaks"):
        result = run_gitleaks(root, history)
    if result is None:
        if engine not in ("auto", "builtin"):
            return {"engine": engine, "status": "error", "findings": [], "accepted": 0,
                    "notes": [f"{engine} is not installed"]}
        findings = scan_worktree(root, exclude)
        engine_used = "built-in"
        if history:
            hist = scan_history(root, exclude)
            known = {f["fingerprint"] for f in findings}
            findings += [f for f in hist["findings"] if f["fingerprint"] not in known]
            notes.append(f"history: {hist['commits']} commit(s) scanned" if hist["scanned"]
                         else f"history not scanned ({hist['note']})")
            if hist["note"] and hist["scanned"]:
                notes.append(hist["note"])
        notes.append("built-in engine: fewer detectors than TruffleHog and no live-key verification; "
                     "install trufflehog or gitleaks to use them instead")
        ok = True
    else:
        findings, engine_used, ok = result["findings"], result["engine"], result["ok"]
        findings = [f for f in findings if not any(str(f["file"]).startswith(p) for p in exclude)]
        if result.get("note"):
            notes.append(result["note"])
    allowed = load_allow(root)
    kept = [f for f in findings if f["fingerprint"] not in allowed]
    status = "error" if not ok else "findings" if kept else "clean"
    return {"engine": engine_used, "status": status, "findings": kept, "accepted": len(findings) - len(kept),
            "notes": notes}
