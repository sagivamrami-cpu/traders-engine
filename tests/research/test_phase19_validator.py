import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase19_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase19.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 19 artifacts validated" in result.stdout


def test_phase19_validator_exercises_prepared_cli_path():
    validator_source = (ROOT / "tools/validate_phase19.py").read_text(encoding="utf-8")

    assert "--project-root" in validator_source
    assert "LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED" in validator_source
