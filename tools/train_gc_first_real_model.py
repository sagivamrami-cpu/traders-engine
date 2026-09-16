from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.models.first_real_gc_model import train_first_real_gc_model
from trading_system.models.readiness import load_training_policy
from trading_system.research.gc_pretraining_readiness import candidate_rows_from_build_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the research-only first real GC predictive model from a built dataset manifest."
    )
    parser.add_argument("--build-manifest", required=True, type=Path, help="Sanitized GC dataset build manifest JSON.")
    parser.add_argument(
        "--rows-root",
        type=Path,
        default=ROOT / "market-data/gc-30m-real",
        help="Local root containing the built rows parquet.",
    )
    parser.add_argument(
        "--training-policy",
        type=Path,
        default=ROOT / "configs/models/baseline-training-policy.yaml",
        help="Training policy YAML.",
    )
    parser.add_argument("--variant", choices=["ohlcv_only", "order_flow"], default="order_flow")
    parser.add_argument("--run-out", required=True, type=Path, help="Write sanitized first-real-model run JSON here.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        _, rows = candidate_rows_from_build_manifest(
            args.build_manifest,
            rows_root=args.rows_root,
            variant=args.variant,
        )
        run = train_first_real_gc_model(
            rows,
            load_training_policy(args.training_policy),
            created_at=datetime.now(UTC),
        )
        payload = run.to_payload()
        validate_json_payload(ROOT / "schemas/gc_first_real_model_run.schema.json", payload)
        text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        args.run_out.parent.mkdir(parents=True, exist_ok=True)
        args.run_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_FIRST_REAL_MODEL_TRAINING_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
