#!/usr/bin/env python3
"""SpecPilot CLI launcher bundled with the skill: python3 scripts/sdd.py <command>."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from specpilot.cli import main

sys.exit(main())
