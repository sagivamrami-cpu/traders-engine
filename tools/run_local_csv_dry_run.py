from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.models.readiness import load_training_policy
from trading_system.research.offline_dry_run import build_local_csv_research_dry_run
from trading_system.research.source_bundle import validate_local_source_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local CSV through the offline research pipeline.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to the local OHLCV CSV file.")
    parser.add_argument("--metadata", required=True, type=Path, help="Path to local CSV source metadata YAML.")
    parser.add_argument(
        "--retention-policy",
        required=True,
        type=Path,
        help="Raw-data retention policy YAML required before dry-run output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created_at = datetime.now(UTC)
    bundle = validate_local_source_bundle(
        args.csv,
        args.metadata,
        args.retention_policy,
        created_at=created_at,
    )
    if bundle.status != "ACCEPTED_FOR_DRY_RUN":
        print(json.dumps(bundle.to_payload(), ensure_ascii=True, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
    dry_run = build_local_csv_research_dry_run(
        args.csv,
        yaml.safe_load(args.metadata.read_text(encoding="utf-8")),
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        load_training_policy(ROOT / "configs/models/baseline-training-policy.yaml"),
        created_at=created_at,
    )
    print(json.dumps(dry_run.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
