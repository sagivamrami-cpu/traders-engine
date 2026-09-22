#!/usr/bin/env python
"""Collect one or more closed UTC days of TR Order Flow evidence."""
from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.databento_daily_orderflow import (  # noqa: E402
    DailyOrderFlowCollector,
    closed_utc_dates,
    create_historical_client,
    load_policy,
    record_blocked_status,
)


def _date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=ROOT / "configs/data/databento-orderflow-daily.json")
    parser.add_argument("--data-root", type=Path, default=ROOT / "market-data/databento-orderflow-daily")
    parser.add_argument("--date", type=_date)
    parser.add_argument("--start", type=_date)
    parser.add_argument("--end", type=_date)
    args = parser.parse_args()

    today = datetime.now(UTC).date()
    if args.date and (args.start or args.end):
        parser.error("use --date or --start/--end")
    if args.date:
        start = end = args.date
    elif args.start or args.end:
        if not (args.start and args.end):
            parser.error("--start and --end are required together")
        start, end = args.start, args.end
    else:
        start = end = today - timedelta(days=1)

    try:
        days = closed_utc_dates(start, end)
    except ValueError as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}))
        return 2

    try:
        client = create_historical_client()
    except ValueError:
        results = [record_blocked_status(args.data_root, day, "BLOCKED_API_KEY_MISSING") for day in days]
        print(json.dumps(results, ensure_ascii=False))
        return 3

    policy = load_policy(args.policy)
    collector = DailyOrderFlowCollector(policy, client, args.data_root)
    results = [collector.collect(day) for day in days]
    print(json.dumps(results, ensure_ascii=False))
    return 0 if all(x["status"] in {"COMPLETE", "ALREADY_COMPLETE"} for x in results) else 4


if __name__ == "__main__":
    raise SystemExit(main())
