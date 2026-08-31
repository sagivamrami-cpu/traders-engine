import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from trading_system.research.readiness import (
    build_real_data_readiness_report,
    load_real_data_decisions,
    load_real_data_readiness_checklist,
)

ROOT = Path(__file__).resolve().parents[2]
CHECKLIST_PATH = ROOT / "configs/research/real-data-readiness-checklist.yaml"
DECISIONS_TEMPLATE_PATH = ROOT / "configs/research/real-data-decisions-template.yaml"


def validate_payload(schema_name: str, payload: dict) -> None:
    schema = json.loads((ROOT / f"schemas/{schema_name}").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def report():
    return build_real_data_readiness_report(
        load_real_data_readiness_checklist(CHECKLIST_PATH),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )


def test_real_data_readiness_checklist_config_validates_against_schema():
    payload = yaml.safe_load(CHECKLIST_PATH.read_text(encoding="utf-8"))

    validate_payload("real_data_readiness_report.schema.json", report().to_payload())
    assert payload["version"] == "real-data-readiness-checklist-0.1.0"
    assert len(payload["required_items"]) >= 6


def test_default_real_data_readiness_report_remains_blocked():
    payload = report().to_payload()

    assert payload["status"] == "BLOCKED"
    assert payload["satisfied_count"] == 0
    assert payload["open_count"] == payload["required_count"]
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in payload["blocked_actions"]
    assert "TRAIN_PRODUCTION_MODEL" in payload["blocked_actions"]
    assert "LIVE_TRADING" in payload["blocked_actions"]


def test_required_human_inputs_are_explicit():
    payload = report().to_payload()
    item_ids = {item["item_id"] for item in payload["required_items"]}

    assert "REAL_HISTORICAL_OHLCV_CSV" in item_ids
    assert "FIRST_REAL_SYMBOL" in item_ids
    assert "FIRST_HISTORICAL_INTERVAL" in item_ids
    assert "RAW_DATA_STORAGE_LICENSE_APPROVAL" in item_ids
    assert "ORDER_FLOW_SOURCE_DECISION" in item_ids
    assert "OPTIONS_SOURCE_DECISION" in item_ids
    assert "PRODUCTION_OHLCV_VENDOR_DECISION" in item_ids


def test_no_required_item_is_satisfied_by_default():
    payload = report().to_payload()

    assert all(item["status"] == "OPEN_HUMAN_DECISION" for item in payload["required_items"])


def decision_entry(item_id: str = "REAL_HISTORICAL_OHLCV_CSV", **overrides) -> dict:
    entry = {
        "item_id": item_id,
        "decision": "APPROVED",
        "approver": "Test Human Approver",
        "decided_at": "2026-08-31T00:00:00Z",
        "scope": "Approve one local real OHLCV CSV for research dataset construction.",
        "evidence": ["agent-exchange/decisions/2026-08-31T000000Z-human-real-csv-approval.md"],
    }
    entry.update(overrides)
    return {key: value for key, value in entry.items() if value is not None}


def write_decision_record(tmp_path: Path, relative_path: str = "agent-exchange/decisions/2026-08-31T000000Z-human-real-csv-approval.md") -> Path:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Human Decision\n\n"
        "Approver:\n"
        "Test Human Approver\n\n"
        "Created at:\n"
        "2026-08-31T00:00:00Z\n\n"
        "Scope:\n"
        "Approve one local real OHLCV CSV for research dataset construction.\n\n"
        "Decision:\n"
        "APPROVED\n\n"
        "Evidence:\n"
        "- source owner approval\n",
        encoding="utf-8",
    )
    return path


def write_decisions(tmp_path: Path, entries: list[dict]) -> Path:
    write_decision_record(tmp_path)
    path = tmp_path / "agent-exchange/decisions/decisions.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": "real-data-decisions-0.1.0", "decisions": entries}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def report_with_decisions(decisions):
    return build_real_data_readiness_report(
        load_real_data_readiness_checklist(CHECKLIST_PATH),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        decisions=decisions,
    )


def test_default_report_has_null_decisions_version():
    payload = report().to_payload()

    assert payload["decisions_version"] is None


def test_decisions_template_validates_against_decisions_schema():
    payload = yaml.safe_load(DECISIONS_TEMPLATE_PATH.read_text(encoding="utf-8"))

    validate_payload("real_data_decisions.schema.json", payload)
    assert payload["version"] == "real-data-decisions-0.1.0"


def test_decisions_template_does_not_satisfy_any_item():
    payload = report_with_decisions(load_real_data_decisions(DECISIONS_TEMPLATE_PATH)).to_payload()

    validate_payload("real_data_readiness_report.schema.json", payload)
    assert payload["status"] == "BLOCKED"
    assert payload["satisfied_count"] == 0


def test_approved_decision_with_full_evidence_satisfies_known_item(tmp_path):
    decisions = load_real_data_decisions(write_decisions(tmp_path, [decision_entry()]))

    payload = report_with_decisions(decisions).to_payload()

    validate_payload("real_data_readiness_report.schema.json", payload)
    assert payload["status"] == "BLOCKED"
    assert payload["satisfied_count"] == 1
    assert payload["decisions_version"] == "real-data-decisions-0.1.0"
    item = next(i for i in payload["required_items"] if i["item_id"] == "REAL_HISTORICAL_OHLCV_CSV")
    assert item["status"] == "SATISFIED"
    assert item["decision"]["approver"] == "Test Human Approver"
    assert item["decision"]["evidence"]


def test_approved_decision_file_outside_decisions_directory_fails(tmp_path):
    write_decision_record(tmp_path)
    path = tmp_path / "configs/research/agent-authored-decisions.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"version": "real-data-decisions-0.1.0", "decisions": [decision_entry()]},
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="agent-exchange/decisions"):
        load_real_data_decisions(path)


def test_approved_decision_requires_existing_markdown_evidence_under_decisions(tmp_path):
    missing = decision_entry(
        evidence=["agent-exchange/decisions/does-not-exist.md"],
    )
    outside = decision_entry(
        evidence=["agent-exchange/status/2026-08-31T120000Z-codex-phase-14-implementation-status.md"],
    )

    with pytest.raises(ValueError, match="evidence path"):
        load_real_data_decisions(write_decisions(tmp_path, [missing]))
    with pytest.raises(ValueError, match="agent-exchange/decisions"):
        load_real_data_decisions(write_decisions(tmp_path, [outside]))


def test_deferred_decision_does_not_satisfy_vendor_approval(tmp_path):
    entry = decision_entry(
        item_id="PRODUCTION_OHLCV_VENDOR_DECISION",
        decision="DEFERRED",
        scope="Use local-only research data for now; no vendor is approved.",
    )
    decisions = load_real_data_decisions(write_decisions(tmp_path, [entry]))

    payload = report_with_decisions(decisions).to_payload()

    assert payload["status"] == "BLOCKED"
    assert payload["satisfied_count"] == 0
    item = next(i for i in payload["required_items"] if i["item_id"] == "PRODUCTION_OHLCV_VENDOR_DECISION")
    assert item["status"] == "OPEN_HUMAN_DECISION"
    assert item["decision"]["decision"] == "DEFERRED"


def test_report_id_changes_when_decision_evidence_changes(tmp_path):
    first = load_real_data_decisions(write_decisions(tmp_path, [decision_entry()]))
    write_decision_record(tmp_path, "agent-exchange/decisions/2026-08-31T000001Z-human-real-csv-approval.md")
    second = load_real_data_decisions(
        write_decisions(
            tmp_path,
            [
                decision_entry(
                    evidence=[
                        "agent-exchange/decisions/2026-08-31T000001Z-human-real-csv-approval.md"
                    ]
                )
            ],
        )
    )

    assert report_with_decisions(first).report_id != report_with_decisions(second).report_id


def test_all_items_approved_yields_ready_status(tmp_path):
    checklist = load_real_data_readiness_checklist(CHECKLIST_PATH)
    for index, _item in enumerate(checklist.required_items):
        write_decision_record(
            tmp_path,
            f"agent-exchange/decisions/2026-08-31T00000{index}Z-human-real-csv-approval.md",
        )
    entries = [decision_entry(item.item_id) for item in checklist.required_items]
    for index, entry in enumerate(entries):
        entry["evidence"] = [
            f"agent-exchange/decisions/2026-08-31T00000{index}Z-human-real-csv-approval.md"
        ]
    decisions = load_real_data_decisions(write_decisions(tmp_path, entries))

    payload = build_real_data_readiness_report(
        checklist,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        decisions=decisions,
    ).to_payload()

    validate_payload("real_data_readiness_report.schema.json", payload)
    assert payload["status"] == "BLOCKED"
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in payload["blocked_actions"]
    assert payload["open_count"] == 0
    assert payload["satisfied_count"] == payload["required_count"]


def test_not_approved_decision_does_not_satisfy(tmp_path):
    entry = decision_entry(decision="NOT_APPROVED")
    decisions = load_real_data_decisions(write_decisions(tmp_path, [entry]))

    payload = report_with_decisions(decisions).to_payload()

    validate_payload("real_data_readiness_report.schema.json", payload)
    assert payload["status"] == "BLOCKED"
    assert payload["satisfied_count"] == 0
    item = next(i for i in payload["required_items"] if i["item_id"] == "REAL_HISTORICAL_OHLCV_CSV")
    assert item["status"] == "OPEN_HUMAN_DECISION"
    assert item["decision"]["decision"] == "NOT_APPROVED"


def test_unknown_decision_item_id_fails(tmp_path):
    decisions = load_real_data_decisions(
        write_decisions(tmp_path, [decision_entry("NOT_A_KNOWN_CHECKLIST_ITEM")])
    )

    with pytest.raises(ValueError, match="unknown"):
        report_with_decisions(decisions)


def test_duplicate_decision_item_id_fails(tmp_path):
    decisions = load_real_data_decisions(
        write_decisions(tmp_path, [decision_entry(), decision_entry()])
    )

    with pytest.raises(ValueError, match="duplicate"):
        report_with_decisions(decisions)


def test_missing_approver_fails_loader_and_schema(tmp_path):
    entry = decision_entry(approver=None)

    with pytest.raises(ValueError, match="approver"):
        load_real_data_decisions(write_decisions(tmp_path, [entry]))
    with pytest.raises(ValidationError):
        validate_payload(
            "real_data_decisions.schema.json",
            {"version": "real-data-decisions-0.1.0", "decisions": [entry]},
        )


def test_missing_evidence_fails_loader_and_schema(tmp_path):
    for entry in (decision_entry(evidence=None), decision_entry(evidence=[])):
        with pytest.raises(ValueError, match="evidence"):
            load_real_data_decisions(write_decisions(tmp_path, [entry]))
        with pytest.raises(ValidationError):
            validate_payload(
                "real_data_decisions.schema.json",
                {"version": "real-data-decisions-0.1.0", "decisions": [entry]},
            )


def test_invalid_decision_value_fails_loader(tmp_path):
    entry = decision_entry(decision="MAYBE")

    with pytest.raises(ValueError, match="decision"):
        load_real_data_decisions(write_decisions(tmp_path, [entry]))


def test_wrong_decisions_version_fails_loader(tmp_path):
    path = tmp_path / "decisions.yaml"
    payload = {"version": "real-data-decisions-9.9.9", "decisions": [decision_entry()]}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="version"):
        load_real_data_decisions(path)


def test_fixture_or_synthetic_evidence_cannot_satisfy(tmp_path):
    write_decision_record(tmp_path, "agent-exchange/decisions/fixture-evidence.md")
    fixture_entry = decision_entry(
        evidence=["agent-exchange/decisions/fixture-evidence.md"]
    )
    synthetic_entry = decision_entry(
        scope="Approve synthetic OHLCV generated for testing."
    )

    for entry in (fixture_entry, synthetic_entry):
        decisions = load_real_data_decisions(write_decisions(tmp_path, [entry]))
        with pytest.raises(ValueError, match="fixture|synthetic"):
            report_with_decisions(decisions)
