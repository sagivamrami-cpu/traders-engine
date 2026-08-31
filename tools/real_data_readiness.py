from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.readiness import (
    build_real_data_readiness_report,
    load_real_data_decisions,
    load_real_data_readiness_checklist,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the real-data readiness report as JSON.")
    parser.add_argument(
        "--decisions",
        type=Path,
        default=None,
        help="Optional human-maintained real-data decision YAML file to merge.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checklist = load_real_data_readiness_checklist(ROOT / "configs/research/real-data-readiness-checklist.yaml")
    decisions = load_real_data_decisions(args.decisions) if args.decisions is not None else None
    report = build_real_data_readiness_report(checklist, created_at=datetime.now(UTC), decisions=decisions)
    print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
