import contextlib
import io
import tempfile
from pathlib import Path

from specpilot.cli import main


def tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="sdd-")).resolve()


def sdd(root: Path, *args: str):
    """Run the CLI in-process. Returns (exit_code, combined_output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = main(["--dir", str(root), *args])
        except SystemExit as exc:  # argparse errors
            code = exc.code
    return code, buf.getvalue()


def write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def use_python_e2e(root: Path) -> None:
    """An empty repository defaults to Gherkin. Tests about the Python form pin it explicitly."""
    import json
    cfg_path = root / ".sdd" / "config.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["e2eFramework"] = "playwright-python"
    cfg_path.write_text(json.dumps(cfg))
    from specpilot.gentests import ensure_scaffold
    from specpilot.spec import e2e_dir
    ensure_scaffold(root, e2e_dir(root), "playwright-python")


def without(root: Path, *checks: str) -> None:
    """Switch lifecycle checks off for a test that is about something else."""
    for check in checks:
        code, out = sdd(root, "lifecycle", "skip", check, "--reason", "not the subject of this test")
        assert code == 0, out


def feature(root: Path, name="f1", spec=None, plan=None, tasks=None):
    for fname, body in (("spec.md", spec), ("plan.md", plan), ("tasks.md", tasks)):
        if body is not None:
            write(root, f".sdd/specs/{name}/{fname}", body)
