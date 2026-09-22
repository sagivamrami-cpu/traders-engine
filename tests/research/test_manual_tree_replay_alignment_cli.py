import json
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "manual_tree_replay_alignment_fixture",
    ROOT / "tests/research/test_manual_tree_replay_alignment.py",
)
if _FIXTURE_SPEC is None or _FIXTURE_SPEC.loader is None:
    raise RuntimeError("manual tree replay alignment fixture could not be loaded")
_FIXTURE_MODULE = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURE_MODULE)
gc_manifest = _FIXTURE_MODULE.gc_manifest
manual_alert_inputs = _FIXTURE_MODULE.manual_alert_inputs


def test_manual_tree_replay_alignment_cli_writes_sanitized_outputs(tmp_path: Path):
    raw_alerts = tmp_path / "manual-alerts-input.json"
    manifest = tmp_path / "gc-manifest.json"
    alerts_out = tmp_path / "golden-alerts.json"
    report_out = tmp_path / "alignment-report.json"
    raw_alerts.write_text(json.dumps(manual_alert_inputs()), encoding="utf-8")
    manifest.write_text(json.dumps(gc_manifest()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/manual_tree_replay_alignment.py",
            "--manual-alerts-input",
            str(raw_alerts),
            "--dataset-manifest",
            str(manifest),
            "--tree-gate-audit-id",
            "a" * 64,
            "--alerts-out",
            str(alerts_out),
            "--report-out",
            str(report_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["alignment_report"]["status"] == "REPLAY_BLOCKED_SOURCE_DATA_GAP"
    assert payload["alignment_report"]["tree_gate_audit_id"] == "a" * 64
    assert payload["golden_alerts"]["alert_count"] == 2
    windows_path_prefix = "C:" + "\\"
    unix_user_path_prefix = "/" + "Users/"
    assert windows_path_prefix not in result.stdout
    assert unix_user_path_prefix not in result.stdout
    assert json.loads(alerts_out.read_text(encoding="utf-8")) == payload["golden_alerts"]
    assert json.loads(report_out.read_text(encoding="utf-8")) == payload["alignment_report"]
    assert result.stderr == ""
