import subprocess
import sys


def test_phase15_validator_command_passes():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase15.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Phase 15 artifacts validated" in result.stdout
