import sys
from pathlib import Path

# The package lives inside the skill so that the repository is directly installable as a skill.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "specpilot" / "scripts"))
