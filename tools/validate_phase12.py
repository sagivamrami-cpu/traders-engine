from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.research.readiness import (
    build_real_data_readiness_report,
    load_real_data_readiness_checklist,
)


def main() -> None:
    schema_path = ROOT / "schemas/real_data_readiness_report.schema.json"
    checklist = load_real_data_readiness_checklist(ROOT / "configs/research/real-data-readiness-checklist.yaml")
    report = build_real_data_readiness_report(
        checklist,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    payload = report.to_payload()
    validate_json_payload(schema_path, payload)
    if payload["status"] != "BLOCKED":
        raise ValueError("default real-data readiness must remain blocked")
    if payload["satisfied_count"] != 0:
        raise ValueError("no real-data readiness item may be satisfied by default")

    cli_result = subprocess.run(
        [sys.executable, str(ROOT / "tools/real_data_readiness.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    validate_json_payload(schema_path, json.loads(cli_result.stdout))
    print("Phase 12 artifacts validated")


if __name__ == "__main__":
    main()
