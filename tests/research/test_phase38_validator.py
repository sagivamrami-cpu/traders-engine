import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase38_validator_accepts_canonical_order_flow_input_manifest():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase38.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 38 artifacts validated" in result.stdout
    assert result.stderr == ""
