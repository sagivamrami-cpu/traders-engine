import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase21_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase21.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 21 artifacts validated" in result.stdout
