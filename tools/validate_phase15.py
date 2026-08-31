from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.csv_inspection import inspect_local_ohlcv_csv
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.research.readiness import (
    build_real_data_readiness_report,
    load_real_data_decisions,
    load_real_data_readiness_checklist,
)

CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)


def _valid_csv(path: Path) -> Path:
    fixture_csv = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
    path.write_text(
        fixture_csv.read_text(encoding="utf-8").replace(
            "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
            "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
        ),
        encoding="utf-8",
    )
    return path


def _metadata_inputs() -> dict[str, str]:
    return {
        "source_id": "local-csv-ohlcv-spy",
        "canonical_symbol": "TR_FIXTURE_SPY",
        "asset_class": "EQUITY_ETF",
        "venue": "LOCAL_CSV",
        "timeframe": "1m",
        "session_calendar_id": "us-equities-regular-v1",
        "owner": "Human Data Owner",
    }


def _write_decision_record(root: Path) -> None:
    path = root / "agent-exchange/decisions/2026-08-31T000000Z-human-real-csv-approval.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Human Decision\n\n"
        "Approver:\n"
        "Phase 15 Validator\n\n"
        "Created at:\n"
        "2026-08-31T00:00:00Z\n\n"
        "Scope:\n"
        "Approve one local real OHLCV CSV for research dataset construction.\n\n"
        "Decision: APPROVED\n\n"
        "Evidence:\n"
        "- validator fixture record\n",
        encoding="utf-8",
    )


def _write_decisions(root: Path, destination: Path) -> Path:
    payload = {
        "version": "real-data-decisions-0.1.0",
        "decisions": [
            {
                "item_id": "REAL_HISTORICAL_OHLCV_CSV",
                "decision": "APPROVED",
                "approver": "Phase 15 Validator",
                "decided_at": "2026-08-31T00:00:00Z",
                "scope": "Approve one local real OHLCV CSV for research dataset construction.",
                "evidence": [
                    "agent-exchange/decisions/2026-08-31T000000Z-human-real-csv-approval.md"
                ],
            }
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return destination


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    checklist = load_real_data_readiness_checklist(ROOT / "configs/research/real-data-readiness-checklist.yaml")
    report_schema_path = ROOT / "schemas/real_data_readiness_report.schema.json"
    inspection_schema_path = ROOT / "schemas/local_csv_inspection_report.schema.json"
    fixture_csv = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
    metadata_path = ROOT / "configs/data/local-csv-onboarding-template.yaml"
    retention_policy_path = ROOT / "configs/data/raw-data-retention-policy.yaml"
    policy = load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(ROOT / "configs/data/symbol-map.yaml")

    default_payload = build_real_data_readiness_report(checklist, created_at=CREATED_AT).to_payload()
    validate_json_payload(report_schema_path, default_payload)
    _require(default_payload["status"] == "BLOCKED", "default readiness must stay blocked")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        _write_decision_record(temp_root)
        outside_yaml = _write_decisions(temp_root, temp_root / "configs/research/decisions.yaml")
        try:
            load_real_data_decisions(outside_yaml)
        except ValueError:
            pass
        else:
            raise ValueError("approved decision YAML outside agent-exchange/decisions must fail")

        decisions_yaml = _write_decisions(temp_root, temp_root / "agent-exchange/decisions/decisions.yaml")
        decisions = load_real_data_decisions(decisions_yaml)
        decided_payload = build_real_data_readiness_report(
            checklist,
            created_at=CREATED_AT,
            decisions=decisions,
        ).to_payload()
        validate_json_payload(report_schema_path, decided_payload)
        _require(decided_payload["status"] == "BLOCKED", "approved item must not imply production readiness")

        valid_csv = _valid_csv(temp_root / "valid.csv")
        inspection = inspect_local_ohlcv_csv(
            valid_csv,
            _metadata_inputs(),
            policy,
            symbol_map,
            created_at=CREATED_AT,
        ).to_payload()
        validate_json_payload(inspection_schema_path, inspection)
        _require(
            inspection["status"] == "SHAPE_VALIDATED_NEEDS_BUNDLE_VALIDATION",
            "inspection must not imply bundle acceptance",
        )

    missing_retention = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/run_local_csv_dry_run.py"),
            "--csv",
            str(fixture_csv),
            "--metadata",
            str(metadata_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    _require(missing_retention.returncode != 0, "dry-run CLI must require retention policy")

    gated_dry_run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/run_local_csv_dry_run.py"),
            "--csv",
            str(fixture_csv),
            "--metadata",
            str(metadata_path),
            "--retention-policy",
            str(retention_policy_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(gated_dry_run.stdout)
    validate_json_payload(ROOT / "schemas/offline_research_run.schema.json", payload)
    _require(payload["safety_status"] == "BLOCKED_FOR_RESEARCH_ONLY", "dry-run must stay research-only")

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    _require("*.csv" in gitignore, "real CSV exports must be gitignored")
    _require("!tests/fixtures/**/*.csv" in gitignore, "fixture CSVs must remain allowed")

    print("Phase 15 artifacts validated")


if __name__ == "__main__":
    main()
