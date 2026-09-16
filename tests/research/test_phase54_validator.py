import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase54_validator_accepts_walk_forward_experiments_report():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase54.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 54 artifacts validated" in result.stdout
    assert result.stderr == ""
