import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase56_validator_accepts_tree_translation_gap_review():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase56.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 56 artifacts validated" in result.stdout
    assert result.stderr == ""
