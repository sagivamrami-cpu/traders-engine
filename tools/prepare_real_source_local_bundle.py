from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.real_source_local_bundle import build_real_source_local_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a sanitized local-only real-source bundle packet."
    )
    parser.add_argument("--csv", required=True, type=Path, help="Path to the local OHLCV CSV file.")
    parser.add_argument("--metadata", required=True, type=Path, help="Path to source metadata YAML.")
    parser.add_argument(
        "--decisions",
        type=Path,
        default=None,
        help="Optional human-maintained real-data decision YAML file.",
    )
    parser.add_argument(
        "--retention-policy",
        required=True,
        type=Path,
        help="Path to the raw-data retention policy YAML.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Optional project root for resolving temporary policies and decision records.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        bundle = build_real_source_local_bundle(
            args.csv,
            args.metadata,
            args.decisions,
            args.retention_policy,
            created_at=datetime.now(UTC),
            project_root=args.project_root,
        )
    except Exception:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error": "LOCAL_REAL_SOURCE_BUNDLE_PREPARATION_FAILED",
                    "csv_path": "LOCAL_PATH_REDACTED",
                    "metadata_path": "LOCAL_PATH_REDACTED",
                    "decisions_path": "LOCAL_PATH_REDACTED",
                    "retention_policy_path": "LOCAL_PATH_REDACTED",
                },
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    print(json.dumps(bundle.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
