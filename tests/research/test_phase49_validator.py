import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase49_validator_accepts_diagnostics_report():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase49.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 49 artifacts validated" in result.stdout
    assert result.stderr == ""
