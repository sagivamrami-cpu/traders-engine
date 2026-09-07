from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

ALERTS_PATH = ROOT / "configs/research/xauusd-manual-tree-golden-alerts-2026w36.json"
REPORT_PATH = ROOT / "configs/research/manual-tree-replay-alignment-report.json"
DATASET_MANIFEST_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-build-manifest.json"
TREE_GATE_AUDIT_PATH = ROOT / "configs/models/gc-tree-gate-baseline-audit.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def _contains_local_path(value: object) -> bool:
    if isinstance(value, dict):
        return any(_contains_local_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_local_path(item) for item in value)
    if isinstance(value, str):
        return bool(re.search(r"\b[A-Za-z]:\\", value) or re.search(r"/(Users|home|mnt|tmp)/", value))
    return False


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase57.py")])
    validate_json_payload(ROOT / "schemas/manual_tree_golden_alerts.schema.json", load_json(ALERTS_PATH))
    validate_json_payload(ROOT / "schemas/manual_tree_replay_alignment_report.schema.json", load_json(REPORT_PATH))

    alerts = load_json(ALERTS_PATH)
    report = load_json(REPORT_PATH)
    manifest = load_json(DATASET_MANIFEST_PATH)
    tree_gate_audit = load_json(TREE_GATE_AUDIT_PATH)

    _require(alerts["raw_symbol"] == "XAUUSD", "golden alerts must be XAUUSD")
    _require(alerts["source_timezone"] == "Asia/Jerusalem", "manual alert timezone changed")
    _require(alerts["timestamp_semantics"] == "ALERT_TIME", "timestamp semantics changed")
    _require(alerts["alert_count"] == 15, "expected 15 visible XAUUSD alerts from screenshot")
    _require(alerts["alerts"][0]["alert_utc_time"] == "2026-08-31T05:58:00Z", "first XAUUSD alert UTC mismatch")
    _require(alerts["alerts"][-1]["alert_utc_time"] == "2026-09-04T17:45:00Z", "last XAUUSD alert UTC mismatch")
    _require(report["status"] == "REPLAY_BLOCKED_SOURCE_DATA_GAP", "Phase 58 status changed")
    _require(report["source_golden_set_id"] == alerts["golden_set_id"], "golden set id mismatch")
    _require(report["tree_gate_audit_id"] == tree_gate_audit["audit_id"], "tree gate audit id mismatch")
    _require(report["current_dataset_id"] == manifest["dataset_id"], "dataset id mismatch")
    _require(report["current_dataset_symbol"] == "GC", "current dataset must remain GC")
    _require(report["eligible_for_current_replay_count"] == 0, "current replay eligibility changed")
    for reason in (
        "SYMBOL_MISMATCH_XAUUSD_VS_GC",
        "ALERT_RANGE_AFTER_CURRENT_DATASET_END",
        "XAUUSD_NOT_REGISTERED_IN_SYMBOL_MAP",
    ):
        _require(reason in report["blocked_reasons"], f"blocked reason missing: {reason}")
    _require(report["replay_ready"] is False, "replay must remain blocked")
    _require(report["model_training_allowed"] is False, "model training must remain blocked")
    _require(report["model_promotion_allowed"] is False, "model promotion must remain blocked")
    for action in (
        "RUN_MANUAL_TREE_REPLAY",
        "TRAIN_MODEL_FROM_MANUAL_ALERTS",
        "MAP_XAUUSD_TO_GC_WITHOUT_PROXY_STUDY",
        "MODEL_PROMOTION",
        "LIVE_TRADING",
        "BROKER_EXECUTION",
        "CAPITAL_ALLOCATION",
        "CLAIM_EDGE",
    ):
        _require(action in report["blocked_actions"], f"blocked action missing: {action}")
    _require(
        report["recommended_next_phase"] == "PHASE_59_XAUUSD_REPLAY_DATA_ONBOARDING_OR_PROXY_DECISION",
        "next phase changed",
    )
    _require(not _contains_local_path(alerts), "golden alerts must not contain local machine paths")
    _require(not _contains_local_path(report), "alignment report must not contain local machine paths")

    print("Phase 58 artifacts validated")


if __name__ == "__main__":
    main()
