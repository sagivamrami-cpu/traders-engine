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
from trading_system.models.gc_normalized_feature_candidates import build_gc_normalized_feature_candidates_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sanitized GC normalized feature candidates report.")
    parser.add_argument(
        "--feature-diagnostics",
        type=Path,
        default=ROOT / "configs/models/gc-feature-diagnostics-report.json",
    )
    parser.add_argument(
        "--report-out",
        required=True,
        type=Path,
        help="Write sanitized normalized feature candidates report JSON here.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        feature_diagnostics = load_json(args.feature_diagnostics)
        report = build_gc_normalized_feature_candidates_report(
            feature_diagnostics,
            created_at=datetime.now(UTC),
        )
        payload = report.to_payload()
        validate_json_payload(ROOT / "schemas/gc_normalized_feature_candidates_report.schema.json", payload)
        text = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception:
        print(
            json.dumps(
                {"error": "GC_NORMALIZED_FEATURE_CANDIDATES_FAILED", "status": "BLOCKED"},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
