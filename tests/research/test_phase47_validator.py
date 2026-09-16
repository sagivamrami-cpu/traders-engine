import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase47_validator_accepts_training_start_and_baseline_run():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase47.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 47 artifacts validated" in result.stdout
    assert result.stderr == ""
