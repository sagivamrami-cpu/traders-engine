import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase55_validator_accepts_bounded_walk_forward_run():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase55.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 55 artifacts validated" in result.stdout
    assert result.stderr == ""
