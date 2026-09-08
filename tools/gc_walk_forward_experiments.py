from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload
from trading_system.models.gc_walk_forward_experiments import build_gc_walk_forward_experiments_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the bounded GC walk-forward retraining experiment plan.")
    parser.add_argument(
        "--stability-report",
        type=Path,
        default=ROOT / "configs/models/gc-normalized-model-stability-report.json",
    )
    parser.add_argument("--report-out", required=True, type=Path, help="Write sanitized experiment report JSON here.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        report = build_gc_walk_forward_experiments_report(
            load_json(args.stability_report),
            created_at=datetime.now(UTC),
        )
        payload = report.to_payload()
        validate_json_payload(ROOT / "schemas/gc_walk_forward_experiments_report.schema.json", payload)
        text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_WALK_FORWARD_EXPERIMENTS_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
