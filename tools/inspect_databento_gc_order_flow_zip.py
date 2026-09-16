from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.databento_gc_order_flow_profile import (
    build_databento_gc_order_flow_profile,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a local Databento GC order-flow ZIP safely.")
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--gates", required=True, type=Path)
    parser.add_argument("--decisions", required=True, type=Path)
    parser.add_argument("--max-sample-entries", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        profile = build_databento_gc_order_flow_profile(
            args.zip,
            args.metadata,
            args.gates,
            args.decisions,
            created_at=datetime.now(UTC),
            max_sample_entries=args.max_sample_entries,
        )
        print(json.dumps(profile.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_ORDER_FLOW_PROFILE_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
