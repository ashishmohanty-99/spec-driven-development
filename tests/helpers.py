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


def feature(root: Path, name="f1", spec=None, plan=None, tasks=None):
    for fname, body in (("spec.md", spec), ("plan.md", plan), ("tasks.md", tasks)):
        if body is not None:
            write(root, f".sdd/specs/{name}/{fname}", body)
