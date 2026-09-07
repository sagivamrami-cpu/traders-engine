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
    build_gc_observed_activity_calendar_profile,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only sanitized observed-activity profile for GC session-calendar research."
    )
    parser.add_argument("--zip", required=True, type=Path, help="Path to the local GC 1s ZIP archive.")
    parser.add_argument("--strategy", required=True, type=Path, help="Path to the D2 source strategy YAML.")
    parser.add_argument(
        "--max-sample-entries",
        type=int,
        default=3,
        help="Maximum parquet entries to read for timestamp gap profiling; <=0 reads all entries.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = build_gc_observed_activity_calendar_profile(
            args.zip,
            args.strategy,
            created_at=datetime.now(UTC),
            max_sample_entries=args.max_sample_entries,
        ).to_payload()
    except Exception:
        print(
            json.dumps(
                {
                    "error": "GC_OBSERVED_ACTIVITY_CALENDAR_PROFILE_FAILED",
                    "status": "BLOCKED",
                    "local_path": "LOCAL_PATH_REDACTED",
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
