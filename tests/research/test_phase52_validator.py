import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase52_validator_accepts_normalized_feature_model_run():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase52.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 52 artifacts validated" in result.stdout
    assert result.stderr == ""
