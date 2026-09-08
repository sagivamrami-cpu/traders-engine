from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.source_bundle import validate_local_source_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a local CSV source bundle for research dry-run use.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to the local OHLCV CSV file.")
    parser.add_argument("--metadata", required=True, type=Path, help="Path to local CSV source metadata YAML.")
    parser.add_argument(
        "--retention-policy",
        required=True,
        type=Path,
        help="Path to raw-data retention policy YAML.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validation = validate_local_source_bundle(
        args.csv,
        args.metadata,
        args.retention_policy,
        created_at=datetime.now(UTC),
    )
    print(json.dumps(validation.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
