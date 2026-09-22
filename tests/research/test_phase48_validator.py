import subprocess
import sys
from pathlib import Path

from tools.validate_phase48 import _contains_local_path

ROOT = Path(__file__).resolve().parents[2]


def test_phase48_validator_accepts_first_real_gc_model_run():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase48.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 48 artifacts validated" in result.stdout
    assert result.stderr == ""


def test_phase48_path_safety_detects_common_absolute_paths():
    assert _contains_local_path({"path": "C:\\Users\\roeea\\Desktop\\secret.csv"})
    assert _contains_local_path({"path": "D:\\market-data\\raw.zip"})
    assert _contains_local_path({"path": "/home/roee/raw.zip"})
    assert _contains_local_path({"path": "/mnt/data/raw.zip"})
