import subprocess
import sys


def test_phase6_validator_command_passes():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase6.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Phase 6 artifacts validated" in result.stdout
