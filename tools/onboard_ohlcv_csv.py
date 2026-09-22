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

from trading_system.data_foundation.csv_onboarding import build_raw_source_manifest_for_csv
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Onboard a local OHLCV CSV as a RawSourceManifest JSON payload.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to the local OHLCV CSV file.")
    parser.add_argument("--metadata", required=True, type=Path, help="Path to local CSV source metadata YAML.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = yaml.safe_load(args.metadata.read_text(encoding="utf-8"))
    policy = load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(ROOT / "configs/data/symbol-map.yaml")
    manifest = build_raw_source_manifest_for_csv(
        args.csv,
        metadata,
        policy,
        symbol_map,
        ingested_at=datetime.now(UTC),
    )
    print(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
