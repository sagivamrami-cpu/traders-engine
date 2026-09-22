from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_label_split_policy import build_gc_label_split_policy_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and emit the GC label/split policy report.")
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()

    report = build_gc_label_split_policy_report(
        args.policy,
        created_at=datetime(2026, 9, 1, 22, 0, tzinfo=UTC),
    ).to_payload()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
