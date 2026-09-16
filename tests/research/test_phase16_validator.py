import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase16_validator_runs_successfully():
    completed = subprocess.run(
        [sys.executable, "tools/validate_phase16.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 16 artifacts validated" in completed.stdout
