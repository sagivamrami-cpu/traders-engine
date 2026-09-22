import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase46_validator_accepts_built_real_dataset_manifest():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase46.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 46 artifacts validated" in result.stdout
    assert result.stderr == ""
