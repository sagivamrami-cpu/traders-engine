from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import validate_json_payload

FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
SCHEMA_PATH = ROOT / "schemas/real_source_local_bundle.schema.json"
METADATA_TEMPLATE = ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml"
RETENTION_POLICY = ROOT / "configs/data/raw-data-retention-policy.yaml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _valid_csv_copy(path: Path) -> Path:
    invalid_row = "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05"
    valid_row = "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05"
    path.write_text(FIXTURE_CSV.read_text(encoding="utf-8").replace(invalid_row, valid_row), encoding="utf-8")
    return path


def _write_decision_record(path: Path, *, decision: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "Approver: Human Data Owner",
                "Created at: 2026-08-31T21:00:00Z",
                "Scope: Phase 19 validator temporary record",
                f"Decision: {decision}",
                "Evidence: Temporary validator record; not production approval",
            ]
        ),
        encoding="utf-8",
    )


def _real_source_project(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    project_root = tmp_path / "project"
    (project_root / "configs/data").mkdir(parents=True)
    (project_root / "configs/research").mkdir(parents=True)
    shutil.copyfile(ROOT / "configs/data/normalization-policy.yaml", project_root / "configs/data/normalization-policy.yaml")
    shutil.copyfile(ROOT / "configs/data/source-identity-policy.yaml", project_root / "configs/data/source-identity-policy.yaml")
    shutil.copyfile(ROOT / "configs/data/raw-data-retention-policy.yaml", project_root / "configs/data/raw-data-retention-policy.yaml")
    shutil.copyfile(
        ROOT / "configs/research/real-data-readiness-checklist.yaml",
        project_root / "configs/research/real-data-readiness-checklist.yaml",
    )
    (project_root / "configs/data/symbol-map.yaml").write_text(
        "\n".join(
            [
                "version: symbol-map-0.1.0",
                "symbols:",
                "  - canonical_symbol: SPY.US",
                "    asset_class: EQUITY_ETF",
                "    venue: TEST_REAL_SOURCE",
                "    raw_symbols: [SPY]",
                "    contract_policy: not_applicable",
            ]
        ),
        encoding="utf-8",
    )
    _write_decision_record(project_root / "agent-exchange/decisions/source.md", decision="APPROVED")
    _write_decision_record(project_root / "agent-exchange/decisions/approved.md", decision="APPROVED")
    _write_decision_record(project_root / "agent-exchange/decisions/deferred.md", decision="DEFERRED")
    metadata = yaml.safe_load(METADATA_TEMPLATE.read_text(encoding="utf-8"))
    metadata.update(
        {
            "source_id": "real-ohlcv-spy-1m",
            "asset_class": "EQUITY_ETF",
            "venue": "TEST_REAL_SOURCE",
            "canonical_symbol": "SPY.US",
            "raw_symbol": "SPY",
            "timeframe": "1m",
            "timezone": "America/New_York",
            "session_calendar_id": "us-equities-regular-v1",
            "human_decision_ref": "agent-exchange/decisions/source.md",
        }
    )
    metadata_path = project_root / "configs/data/real-source.yaml"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=True), encoding="utf-8")
    decisions_path = project_root / "agent-exchange/decisions/decisions.yaml"
    decisions_path.write_text(
        yaml.safe_dump(
            {
                "version": "real-data-decisions-0.1.0",
                "decisions": [
                    {
                        "item_id": item_id,
                        "decision": decision,
                        "approver": "Human Data Owner",
                        "decided_at": "2026-08-31T21:00:00Z",
                        "scope": "Phase 19 validator local-only bundle test",
                        "evidence": [f"agent-exchange/decisions/{decision.lower()}.md"],
                    }
                    for item_id, decision in {
                        "REAL_HISTORICAL_OHLCV_CSV": "APPROVED",
                        "PRODUCTION_OHLCV_VENDOR_DECISION": "APPROVED",
                        "FIRST_REAL_SYMBOL": "APPROVED",
                        "FIRST_HISTORICAL_INTERVAL": "APPROVED",
                        "RAW_DATA_STORAGE_LICENSE_APPROVAL": "APPROVED",
                        "ORDER_FLOW_SOURCE_DECISION": "DEFERRED",
                        "OPTIONS_SOURCE_DECISION": "DEFERRED",
                    }.items()
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return (
        project_root,
        metadata_path,
        decisions_path,
        project_root / "configs/data/raw-data-retention-policy.yaml",
    )


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase18.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_real_source_local_bundle.py", "-q"])

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = _valid_csv_copy(Path(tmpdir) / "valid.csv")
        cli_result = _run(
            [
                sys.executable,
                str(ROOT / "tools/prepare_real_source_local_bundle.py"),
                "--csv",
                str(csv_path),
                "--metadata",
                str(METADATA_TEMPLATE),
                "--retention-policy",
                str(RETENTION_POLICY),
            ]
        )
        payload = json.loads(cli_result.stdout)
        validate_json_payload(SCHEMA_PATH, payload)
        _require(payload["status"] == "BLOCKED", "default local bundle must be blocked")
        _require(payload["production_allowed"] is False, "local bundle must not approve production")
        _require(payload["local_manifest"] is None, "blocked local bundle must not carry a manifest")
        _require(payload["allowed_next_actions"] == [], "local bundle must not advertise next actions")
        for forbidden in (
            str(csv_path),
            str(METADATA_TEMPLATE),
            str(RETENTION_POLICY),
            "C:\\",
            "/Users/",
        ):
            _require(forbidden not in cli_result.stdout, "CLI output must not include local paths")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        csv_path = _valid_csv_copy(tmp_path / "valid.csv")
        project_root, metadata_path, decisions_path, retention_path = _real_source_project(tmp_path)
        cli_result = _run(
            [
                sys.executable,
                str(ROOT / "tools/prepare_real_source_local_bundle.py"),
                "--csv",
                str(csv_path),
                "--metadata",
                str(metadata_path),
                "--decisions",
                str(decisions_path),
                "--retention-policy",
                str(retention_path),
                "--project-root",
                str(project_root),
            ]
        )
        payload = json.loads(cli_result.stdout)
        validate_json_payload(SCHEMA_PATH, payload)
        _require(
            payload["status"] == "LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED",
            "prepared local bundle must stay production-blocked",
        )
        _require(
            payload["retention_decision"]["status"] == "BLOCKED",
            "prepared local bundle retention decision must stay blocked",
        )
        _require(
            payload["retention_decision"]["dry_run_output_allowed"] is False,
            "prepared local bundle must not allow dry-run output",
        )
        _require(payload["dry_run_summary"] is None, "prepared local bundle must not run dry-run")
        for forbidden in (
            str(csv_path),
            str(metadata_path),
            str(decisions_path),
            str(retention_path),
            str(project_root),
            "Human Data Owner",
            "APPROVED",
            "DEFERRED",
            "C:\\",
            "/Users/",
        ):
            _require(forbidden not in cli_result.stdout, "prepared CLI output must stay sanitized")

    readiness_result = _run([sys.executable, str(ROOT / "tools/real_data_readiness.py")])
    readiness = json.loads(readiness_result.stdout)
    _require(readiness["status"] == "BLOCKED", "real data readiness must remain blocked")

    print("Phase 19 artifacts validated")


if __name__ == "__main__":
    main()
