import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase34_validator_passes():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase34.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 34 artifacts validated" in result.stdout
    assert result.stderr == ""
