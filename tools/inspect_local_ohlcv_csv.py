from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.csv_inspection import inspect_local_ohlcv_csv
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a local OHLCV CSV and suggest unapproved metadata.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to the local OHLCV CSV file.")
    parser.add_argument("--source-id", required=True, help="Proposed local source id.")
    parser.add_argument("--canonical-symbol", required=True, help="Proposed canonical symbol.")
    parser.add_argument("--asset-class", default="EQUITY_ETF", help="Proposed asset class.")
    parser.add_argument("--venue", default="LOCAL_CSV", help="Proposed venue.")
    parser.add_argument("--timeframe", default="1m", help="CSV bar timeframe.")
    parser.add_argument("--session-calendar-id", default="us-equities-regular-v1", help="Session calendar id.")
    parser.add_argument("--owner", default="Human Data Owner", help="Human owner for the source metadata.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata_inputs = {
        "source_id": args.source_id,
        "canonical_symbol": args.canonical_symbol,
        "asset_class": args.asset_class,
        "venue": args.venue,
        "timeframe": args.timeframe,
        "session_calendar_id": args.session_calendar_id,
        "owner": args.owner,
    }
    report = inspect_local_ohlcv_csv(
        args.csv,
        metadata_inputs,
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        created_at=datetime.now(UTC),
    )
    print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
