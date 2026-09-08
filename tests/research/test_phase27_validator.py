import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase27_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase27.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 27 artifacts validated" in result.stdout
