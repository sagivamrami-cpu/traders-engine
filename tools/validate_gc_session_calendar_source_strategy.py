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
    build_gc_session_calendar_source_strategy_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the GC session-calendar source strategy.")
    parser.add_argument("--strategy", required=True, type=Path, help="Path to the strategy YAML.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = build_gc_session_calendar_source_strategy_report(
            args.strategy,
            created_at=datetime.now(UTC),
        ).to_payload()
    except Exception:
        print(
            json.dumps({"error": "GC_SESSION_CALENDAR_SOURCE_STRATEGY_FAILED", "status": "BLOCKED"}),
            file=sys.stderr,
        )
        sys.exit(1)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
