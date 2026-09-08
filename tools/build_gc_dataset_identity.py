from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_dataset_identity import (
    build_gc_dataset_identity,
    compute_local_archive_hashes,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the deterministic GC 30m dataset identity manifest (sanitized: no local paths are printed)."
    )
    parser.add_argument("--config", required=True, type=Path, help="Identity config YAML.")
    parser.add_argument("--ohlcv-zip", type=Path, default=None, help="Local Databento GC 1s ZIP to verify against.")
    parser.add_argument("--order-flow-zip", type=Path, default=None, help="Local Databento GC order-flow ZIP to verify against.")
    parser.add_argument("--write", type=Path, default=None, help="Write the manifest JSON to this repo-relative path.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        local_hashes = None
        if args.ohlcv_zip is not None or args.order_flow_zip is not None:
            paths = {}
            if args.ohlcv_zip is not None:
                paths["ohlcv_1s"] = args.ohlcv_zip
            if args.order_flow_zip is not None:
                paths["order_flow_1m"] = args.order_flow_zip
            local_hashes = compute_local_archive_hashes(paths)
        manifest = build_gc_dataset_identity(
            args.config,
            created_at=datetime.now(UTC),
            local_archive_hashes=local_hashes,
        )
        payload = manifest.to_payload()
        text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        if args.write is not None:
            args.write.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception:
        print(
            json.dumps({"error": "GC_DATASET_IDENTITY_FAILED", "status": "BLOCKED"}, ensure_ascii=True, sort_keys=True),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
