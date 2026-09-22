from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload
from trading_system.models.gc_feature_diagnostics import build_gc_feature_diagnostics_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sanitized GC feature diagnostics report.")
    parser.add_argument(
        "--build-manifest",
        type=Path,
        default=ROOT / "configs/datasets/gc-30m-real-dataset-build-manifest.json",
    )
    parser.add_argument(
        "--rows-root",
        type=Path,
        default=ROOT / "market-data/gc-30m-real",
    )
    parser.add_argument(
        "--first-model-run",
        type=Path,
        default=ROOT / "configs/models/gc-first-real-model-run.json",
    )
    parser.add_argument(
        "--model-diagnostics",
        type=Path,
        default=ROOT / "configs/models/gc-model-diagnostics-report.json",
    )
    parser.add_argument(
        "--report-out",
        required=True,
        type=Path,
        help="Write sanitized feature diagnostics report JSON here.",
    )
    parser.add_argument("--variant", choices=["order_flow"], default="order_flow")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        manifest = load_json(args.build_manifest)
        rows_path = args.rows_root / str(manifest["rows_relative_dir"]) / str(manifest["rows_file"])
        rows = pd.read_parquet(rows_path)
        report = build_gc_feature_diagnostics_report(
            rows,
            manifest,
            load_json(args.first_model_run),
            load_json(args.model_diagnostics),
            created_at=datetime.now(UTC),
            variant=args.variant,
        )
        payload = report.to_payload()
        validate_json_payload(ROOT / "schemas/gc_feature_diagnostics_report.schema.json", payload)
        text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_FEATURE_DIAGNOSTICS_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
