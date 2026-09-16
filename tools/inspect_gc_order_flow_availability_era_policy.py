from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_order_flow_availability_era_policy import (
    build_gc_order_flow_availability_era_policy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a local GC order-flow availability-era policy safely.")
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--gates", required=True, type=Path)
    parser.add_argument("--decisions", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        report = build_gc_order_flow_availability_era_policy(
            args.zip,
            args.gates,
            args.decisions,
            created_at=datetime.now(UTC),
        )
        print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_ORDER_FLOW_AVAILABILITY_ERA_POLICY_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
