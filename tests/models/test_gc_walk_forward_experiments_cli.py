import json
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "gc_walk_forward_experiments_fixture",
    ROOT / "tests/models/test_gc_walk_forward_experiments.py",
)
if _FIXTURE_SPEC is None or _FIXTURE_SPEC.loader is None:
    raise RuntimeError("walk-forward experiments fixture could not be loaded")
_FIXTURE_MODULE = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURE_MODULE)
stability_report = _FIXTURE_MODULE.stability_report


def test_gc_walk_forward_experiments_cli_writes_sanitized_report(tmp_path: Path):
    stability_path = tmp_path / "stability-report.json"
    report_out = tmp_path / "walk-forward-experiments.json"
    stability_path.write_text(json.dumps(stability_report()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/gc_walk_forward_experiments.py",
            "--stability-report",
            str(stability_path),
            "--report-out",
            str(report_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "WALK_FORWARD_EXPERIMENTS_READY"
    assert payload["model_promotion_allowed"] is False
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(report_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""
