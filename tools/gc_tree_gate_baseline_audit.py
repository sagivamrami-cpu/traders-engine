from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload
from trading_system.models.gc_tree_gate_baseline import build_gc_tree_gate_baseline_audit
from trading_system.research.gc_pretraining_readiness import candidate_rows_from_build_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a conservative GC rule-only tree gate baseline audit.")
    parser.add_argument(
        "--build-manifest",
        type=Path,
        default=ROOT / "configs/datasets/gc-30m-real-dataset-build-manifest.json",
    )
    parser.add_argument(
        "--rows-root",
        type=Path,
        default=ROOT / "market-data/gc-30m-real",
        help="Local root containing the built rows parquet.",
    )
    parser.add_argument(
        "--tree-gap-review",
        type=Path,
        default=ROOT / "configs/models/gc-tree-translation-gap-review.json",
    )
    parser.add_argument("--variant", choices=["order_flow"], default="order_flow")
    parser.add_argument("--audit-out", required=True, type=Path, help="Write sanitized tree gate audit JSON here.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        _, rows = candidate_rows_from_build_manifest(
            args.build_manifest,
            rows_root=args.rows_root,
            variant=args.variant,
        )
        audit = build_gc_tree_gate_baseline_audit(
            rows,
            load_json(args.tree_gap_review),
            created_at=datetime.now(UTC),
        )
        payload = audit.to_payload()
        validate_json_payload(ROOT / "schemas/gc_tree_gate_baseline_audit.schema.json", payload)
        text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        args.audit_out.parent.mkdir(parents=True, exist_ok=True)
        args.audit_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_TREE_GATE_BASELINE_AUDIT_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
