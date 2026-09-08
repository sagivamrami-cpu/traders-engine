import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase39_validator_accepts_row_mask_and_cumulative_policy():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase39.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 39 artifacts validated" in result.stdout
    assert result.stderr == ""
