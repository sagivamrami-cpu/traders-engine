import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase57_validator_accepts_tree_gate_baseline_audit():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase57.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 57 artifacts validated" in result.stdout
    assert result.stderr == ""
