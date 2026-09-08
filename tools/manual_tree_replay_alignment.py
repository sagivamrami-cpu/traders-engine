from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload
from trading_system.research.manual_tree_replay_alignment import (
    build_manual_tree_golden_alerts,
    build_manual_tree_replay_alignment_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build manual tree golden alerts and replay alignment report.")
    parser.add_argument(
        "--manual-alerts-input",
        type=Path,
        default=ROOT / "configs/research/xauusd-manual-tree-alerts-2026w36.input.json",
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=ROOT / "configs/datasets/gc-30m-real-dataset-build-manifest.json",
    )
    parser.add_argument("--symbol-map", type=Path, default=ROOT / "configs/data/symbol-map.yaml")
    parser.add_argument(
        "--tree-gate-audit",
        type=Path,
        default=ROOT / "configs/models/gc-tree-gate-baseline-audit.json",
    )
    parser.add_argument("--tree-gate-audit-id", type=str, default=None)
    parser.add_argument(
        "--alerts-out",
        type=Path,
        default=ROOT / "configs/research/xauusd-manual-tree-golden-alerts-2026w36.json",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=ROOT / "configs/research/manual-tree-replay-alignment-report.json",
    )
    return parser.parse_args()


def _load_symbol_map(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    try:
        args = parse_args()
        audit_id = args.tree_gate_audit_id
        if audit_id is None:
            audit_id = str(load_json(args.tree_gate_audit)["audit_id"])
        golden_alerts = build_manual_tree_golden_alerts(
            json.loads(args.manual_alerts_input.read_text(encoding="utf-8")),
            created_at=datetime.now(UTC),
            source_timezone="Asia/Jerusalem",
        ).to_payload()
        alignment_report = build_manual_tree_replay_alignment_report(
            golden_alerts,
            load_json(args.dataset_manifest),
            symbol_map=_load_symbol_map(args.symbol_map),
            tree_gate_audit_id=audit_id,
            created_at=datetime.now(UTC),
        ).to_payload()
        validate_json_payload(ROOT / "schemas/manual_tree_golden_alerts.schema.json", golden_alerts)
        validate_json_payload(ROOT / "schemas/manual_tree_replay_alignment_report.schema.json", alignment_report)
        alerts_text = json.dumps(golden_alerts, ensure_ascii=True, indent=2, sort_keys=True)
        report_text = json.dumps(alignment_report, ensure_ascii=True, indent=2, sort_keys=True)
        args.alerts_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.alerts_out.write_text(alerts_text + "\n", encoding="utf-8")
        args.report_out.write_text(report_text + "\n", encoding="utf-8")
        print(json.dumps({"golden_alerts": golden_alerts, "alignment_report": alignment_report}, ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "MANUAL_TREE_REPLAY_ALIGNMENT_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
