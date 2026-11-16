#!/usr/bin/env python3
"""Build the standalone SpecPilot skill: dist/specpilot/ and dist/specpilot-skill.zip.

The skill bundles the CLI and the wiki pages, so one file is everything a user needs:
    python3 tools/build_skill.py
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "specpilot"
REFERENCES = ["Step-by-Step-Workflow", "SDD-and-the-AI-SDLC", "Test-Automation", "Penetration-Testing",
              "Security-Model", "CLI-Reference", "Extending", "Troubleshooting"]
LAUNCHER = '''#!/usr/bin/env python3
"""SpecPilot CLI launcher bundled with the skill: python3 scripts/sdd.py <command>."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from specpilot.cli import main  # noqa: E402

sys.exit(main())
'''
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # reproducible archives


def build(out: Path) -> Path:
    skill = out / NAME
    if skill.exists():
        shutil.rmtree(skill)
    (skill / "scripts").mkdir(parents=True)
    (skill / "references").mkdir()
    shutil.copy2(ROOT / "skill" / "SKILL.md", skill / "SKILL.md")
    shutil.copy2(ROOT / "LICENSE", skill / "LICENSE")
    shutil.copytree(ROOT / "specpilot", skill / "scripts" / "specpilot",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (skill / "scripts" / "sdd.py").write_text(LAUNCHER, encoding="utf-8")
    for page in REFERENCES:
        shutil.copy2(ROOT / "wiki" / f"{page}.md", skill / "references" / f"{page}.md")

    archive = out / f"{NAME}-skill.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(str(Path(NAME) / path.relative_to(skill)), FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o755 if path.name == "sdd.py" else 0o644) << 16
                zf.writestr(info, path.read_bytes())
    return archive


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "dist"
    target.mkdir(parents=True, exist_ok=True)
    result = build(target)
    print(f"Built {result} ({result.stat().st_size // 1024} KB)")
