from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.readiness import (
    build_real_data_readiness_report,
    load_real_data_readiness_checklist,
)


def main() -> None:
    checklist = load_real_data_readiness_checklist(ROOT / "configs/research/real-data-readiness-checklist.yaml")
    report = build_real_data_readiness_report(checklist, created_at=datetime.now(UTC))
    print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
