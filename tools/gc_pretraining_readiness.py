from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_pretraining_readiness import (
    build_gc_pretraining_readiness_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the GC pre-training readiness report.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--decisions", required=True, type=Path)
    parser.add_argument("--checklist", required=True, type=Path)
    parser.add_argument("--training-policy", required=True, type=Path)
    parser.add_argument("--groq-phase24-review", type=Path, default=None)
    parser.add_argument("--groq-phase24-intake", type=Path, default=None)
    parser.add_argument("--build-manifest", type=Path, default=None)
    parser.add_argument("--rows-root", type=Path, default=None)
    parser.add_argument("--variant", choices=["ohlcv_only", "order_flow"], default="order_flow")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        report = build_gc_pretraining_readiness_report(
            contract_path=args.contract,
            decisions_path=args.decisions,
            checklist_path=args.checklist,
            training_policy_path=args.training_policy,
            created_at=datetime.now(UTC),
            groq_phase24_review_path=args.groq_phase24_review,
            groq_phase24_intake_path=args.groq_phase24_intake,
            build_manifest_path=args.build_manifest,
            rows_root=args.rows_root,
            variant=args.variant,
        )
        print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_PRETRAINING_READINESS_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
