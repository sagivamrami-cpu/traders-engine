from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_session_calendar_source_strategy import (
    build_gc_observed_activity_full_aggregate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect GC observed activity as sanitized parquet metadata aggregates.")
    parser.add_argument("--zip", required=True, type=Path, help="Local GC 1s zip archive.")
    parser.add_argument("--strategy", required=True, type=Path, help="Path to the source strategy YAML.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        report = build_gc_observed_activity_full_aggregate(
            args.zip,
            args.strategy,
            created_at=datetime.now(UTC),
        )
        print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception:
        print(
            json.dumps({"error": "GC_OBSERVED_ACTIVITY_FULL_AGGREGATE_FAILED", "status": "BLOCKED"}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
