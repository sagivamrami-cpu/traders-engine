import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase26_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase26.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 26 artifacts validated" in result.stdout
