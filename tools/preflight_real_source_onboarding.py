from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.real_source_onboarding import build_real_source_onboarding_preflight


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a redacted real-source onboarding preflight.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to the local OHLCV CSV file.")
    parser.add_argument("--metadata", required=True, type=Path, help="Path to source metadata YAML.")
    parser.add_argument("--decisions", default=None, type=Path, help="Optional real-data decisions YAML.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        preflight = build_real_source_onboarding_preflight(
            args.csv,
            args.metadata,
            args.decisions,
            created_at=datetime.now(UTC),
        )
    except Exception as exc:
        error = {
            "error": "REAL_SOURCE_ONBOARDING_PREFLIGHT_FAILED",
            "error_type": type(exc).__name__,
            "csv_path": "LOCAL_PATH_REDACTED",
            "metadata_path": "LOCAL_PATH_REDACTED",
            "decisions_path": "LOCAL_PATH_REDACTED" if args.decisions is not None else None,
            "production_allowed": False,
        }
        print(json.dumps(error, ensure_ascii=True, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(preflight.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
