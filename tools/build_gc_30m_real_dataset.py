from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_real_dataset_build import build_real_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the authorized GC 30m real research dataset and print a sanitized manifest."
    )
    parser.add_argument("--ohlcv-zip", required=True, type=Path, help="Local Databento GC 1s ZIP.")
    parser.add_argument("--order-flow-zip", required=True, type=Path, help="Local Databento GC order-flow ZIP.")
    parser.add_argument(
        "--identity-config",
        type=Path,
        default=ROOT / "configs/datasets/gc-30m-real-dataset-identity.yaml",
        help="Dataset identity config YAML.",
    )
    parser.add_argument(
        "--identity-manifest",
        type=Path,
        default=ROOT / "configs/datasets/gc-30m-real-dataset-identity-manifest.json",
        help="Committed dataset identity manifest JSON.",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "configs/datasets/gc-30m-real-dataset-contract.yaml",
        help="Authorized dataset contract YAML.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "market-data/gc-30m-real",
        help="Local output directory for rows parquet.",
    )
    parser.add_argument("--manifest-out", required=True, type=Path, help="Write sanitized build manifest JSON here.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        manifest = build_real_dataset(
            ohlcv_zip=args.ohlcv_zip,
            order_flow_zip=args.order_flow_zip,
            identity_config=args.identity_config,
            identity_manifest=args.identity_manifest,
            contract_path=args.contract,
            out_dir=args.out_dir,
            created_at=datetime.now(UTC),
        )
        payload = manifest.to_payload()
        text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_REAL_DATASET_BUILD_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
