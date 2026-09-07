import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase58_validator_accepts_manual_tree_replay_alignment():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase58.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 58 artifacts validated" in result.stdout
    assert result.stderr == ""
