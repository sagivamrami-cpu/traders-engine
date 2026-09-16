from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.gc_cme_calendar_evidence_manifest import (
    build_gc_cme_calendar_evidence_manifest_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the GC CME calendar evidence manifest.")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to the CME evidence manifest YAML.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        report = build_gc_cme_calendar_evidence_manifest_report(
            args.manifest,
            created_at=datetime.now(UTC),
        )
        print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception:
        print(
            json.dumps({"error": "GC_CME_CALENDAR_EVIDENCE_MANIFEST_FAILED", "status": "BLOCKED"}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
