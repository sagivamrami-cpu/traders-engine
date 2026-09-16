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
from trading_system.models.gc_tree_translation_gap_review import build_gc_tree_translation_gap_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review GC walk-forward results against tree translation requirements.")
    parser.add_argument(
        "--walk-forward-run",
        type=Path,
        default=ROOT / "configs/models/gc-bounded-walk-forward-retraining-run.json",
    )
    parser.add_argument("--review-out", required=True, type=Path, help="Write sanitized tree gap review JSON here.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        review = build_gc_tree_translation_gap_review(
            load_json(args.walk_forward_run),
            created_at=datetime.now(UTC),
        )
        payload = review.to_payload()
        validate_json_payload(ROOT / "schemas/gc_tree_translation_gap_review.schema.json", payload)
        text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        args.review_out.parent.mkdir(parents=True, exist_ok=True)
        args.review_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_TREE_TRANSLATION_GAP_REVIEW_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
