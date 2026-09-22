from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.databento_gc_source_profile import build_databento_gc_source_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only sanitized profile of the local Databento GC one-second ZIP archive."
    )
    parser.add_argument("--zip", required=True, type=Path, help="Path to the local Databento GC ZIP archive.")
    parser.add_argument("--metadata", required=True, type=Path, help="Path to the GC source metadata YAML.")
    parser.add_argument("--decisions", required=True, type=Path, help="Path to the human decision YAML.")
    parser.add_argument(
        "--max-sample-entries",
        type=int,
        default=3,
        help="Maximum parquet entries to fully read for structural checks.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        profile = build_databento_gc_source_profile(
            args.zip,
            args.metadata,
            args.decisions,
            created_at=datetime.now(UTC),
            max_sample_entries=args.max_sample_entries,
        )
    except Exception:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error": "DATABENTO_GC_PROFILE_FAILED",
                    "zip_path": "LOCAL_PATH_REDACTED",
                    "metadata_path": "LOCAL_PATH_REDACTED",
                    "decisions_path": "LOCAL_PATH_REDACTED",
                },
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    print(json.dumps(profile.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
