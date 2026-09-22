from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_fine_observed_gap_profile import (
    build_gc_fine_observed_gap_profile,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect fine-grained observed gaps from GC ts_event columns.")
    parser.add_argument("--zip", required=True, type=Path, help="Local GC 1s zip archive.")
    parser.add_argument("--strategy", required=True, type=Path, help="Path to the source strategy YAML.")
    parser.add_argument("--top-n-gaps", type=int, default=20, help="Maximum number of largest gaps to emit.")
    parser.add_argument("--max-members", type=int, default=None, help="Maximum number of parquet members to inspect.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        report = build_gc_fine_observed_gap_profile(
            args.zip,
            args.strategy,
            created_at=datetime.now(UTC),
            top_n_gaps=args.top_n_gaps,
            max_members=args.max_members,
        )
        print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception:
        print(
            json.dumps({"error": "GC_FINE_OBSERVED_GAP_PROFILE_FAILED", "status": "BLOCKED"}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
