import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase51_validator_accepts_normalized_feature_candidates_report():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase51.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 51 artifacts validated" in result.stdout
    assert result.stderr == ""
