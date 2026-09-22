from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml
from jsonschema import ValidationError

from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.research.readiness import (
    RealDataDecision,
    RealDataDecisionFile,
    apply_real_data_decisions,
    build_real_data_readiness_report,
    load_real_data_decisions,
    load_real_data_readiness_checklist,
)

CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)


def _decision(item_id: str, **overrides) -> RealDataDecision:
    fields = {
        "item_id": item_id,
        "decision": "APPROVED",
        "approver": "Phase 14 Validator Probe",
        "decided_at": "2026-08-31T00:00:00Z",
        "scope": "Validator negative-path probe; approves nothing in the repository.",
        "evidence": ("agent-exchange/decisions/example-human-decision-record.md",),
    }
    fields.update(overrides)
    return RealDataDecision(**fields)


def _require_blocked(payload: dict, source: str) -> None:
    if payload["status"] != "BLOCKED":
        raise ValueError(f"{source} readiness must remain blocked")
    if payload["satisfied_count"] != 0:
        raise ValueError(f"{source} readiness must not satisfy any item")


def main() -> None:
    report_schema_path = ROOT / "schemas/real_data_readiness_report.schema.json"
    decisions_schema_path = ROOT / "schemas/real_data_decisions.schema.json"
    template_path = ROOT / "configs/research/real-data-decisions-template.yaml"
    checklist = load_real_data_readiness_checklist(ROOT / "configs/research/real-data-readiness-checklist.yaml")

    template_payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    validate_json_payload(decisions_schema_path, template_payload)

    default_payload = build_real_data_readiness_report(checklist, created_at=CREATED_AT).to_payload()
    validate_json_payload(report_schema_path, default_payload)
    _require_blocked(default_payload, "default")
    if default_payload["decisions_version"] is not None:
        raise ValueError("default readiness report must not carry a decisions version")

    template_decisions = load_real_data_decisions(template_path)
    template_report = build_real_data_readiness_report(
        checklist, created_at=CREATED_AT, decisions=template_decisions
    ).to_payload()
    validate_json_payload(report_schema_path, template_report)
    _require_blocked(template_report, "template-merged")

    unknown = RealDataDecisionFile(
        version="real-data-decisions-0.1.0",
        decisions=(_decision("NOT_A_KNOWN_CHECKLIST_ITEM"),),
    )
    try:
        apply_real_data_decisions(checklist, unknown)
    except ValueError:
        pass
    else:
        raise ValueError("unknown decision item_id must fail validation")

    fixture_evidence = RealDataDecisionFile(
        version="real-data-decisions-0.1.0",
        decisions=(
            _decision(
                checklist.required_items[0].item_id,
                evidence=("tests/fixtures/data_foundation/raw/ohlcv_fixture.csv",),
            ),
        ),
    )
    try:
        apply_real_data_decisions(checklist, fixture_evidence)
    except ValueError:
        pass
    else:
        raise ValueError("fixture evidence must not satisfy real-data readiness")

    incomplete_entry = _decision(checklist.required_items[0].item_id).to_payload()
    incomplete_entry["item_id"] = checklist.required_items[0].item_id
    del incomplete_entry["approver"]
    try:
        validate_json_payload(
            decisions_schema_path,
            {"version": "real-data-decisions-0.1.0", "decisions": [incomplete_entry]},
        )
    except ValidationError:
        pass
    else:
        raise ValueError("a decision without an approver must fail schema validation")

    for cli_args in ([], ["--decisions", str(template_path)]):
        cli_result = subprocess.run(
            [sys.executable, str(ROOT / "tools/real_data_readiness.py"), *cli_args],
            capture_output=True,
            text=True,
            check=True,
        )
        cli_payload = json.loads(cli_result.stdout)
        validate_json_payload(report_schema_path, cli_payload)
        _require_blocked(cli_payload, "CLI")

    print("Phase 14 artifacts validated")


if __name__ == "__main__":
    main()
