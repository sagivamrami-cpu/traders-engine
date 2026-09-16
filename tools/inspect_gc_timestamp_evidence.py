from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_timestamp_evidence import build_gc_timestamp_evidence_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect sanitized GC timestamp evidence.")
    parser.add_argument("--ohlcv-zip", type=Path, required=True)
    parser.add_argument("--order-flow-zip", type=Path, required=True)
    args = parser.parse_args()

    report = build_gc_timestamp_evidence_report(
        ohlcv_zip_path=args.ohlcv_zip,
        order_flow_zip_path=args.order_flow_zip,
        created_at=datetime(2026, 9, 1, 22, 30, tzinfo=UTC),
    ).to_payload()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
