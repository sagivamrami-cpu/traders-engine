import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase53_validator_accepts_stability_report():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase53.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 53 artifacts validated" in result.stdout
    assert result.stderr == ""
