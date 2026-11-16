#!/usr/bin/env python3
"""Zip the skill for hosts that take an upload (claude.ai -> Customize -> Skills).

The skill itself lives, complete, in skills/spec-driven-development-by-ashishmohanty/. This only packages that folder:
    python3 tools/build_skill.py        ->  dist/sdd-skill.zip
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "spec-driven-development-by-ashishmohanty"
SKILL = ROOT / "skills" / NAME
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # reproducible archives


def build(out: Path) -> Path:
    archive = out / "sdd-skill.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SKILL.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                info = zipfile.ZipInfo(str(Path(NAME) / path.relative_to(SKILL)), FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o755 if path.name == "sdd.py" else 0o644) << 16
                zf.writestr(info, path.read_bytes())
    return archive


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "dist"
    target.mkdir(parents=True, exist_ok=True)
    result = build(target)
    print(f"Built {result} ({result.stat().st_size // 1024} KB)")
