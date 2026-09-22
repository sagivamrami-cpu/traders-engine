import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase30_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase30.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 30 artifacts validated" in result.stdout
    assert result.stderr == ""
