import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase36_validator_passes():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase36.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 36 artifacts validated" in result.stdout
    assert result.stderr == ""
