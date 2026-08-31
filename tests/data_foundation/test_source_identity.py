import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.source_identity import (
    load_source_identity_policy,
    validate_source_identity,
)

ROOT = Path(__file__).resolve().parents[2]


def fixture_metadata() -> dict:
    return yaml.safe_load((ROOT / "configs/data/local-csv-onboarding-template.yaml").read_text(encoding="utf-8"))


def validate_policy_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/source_identity_policy.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_source_identity_policy_payload_validates_against_schema():
    payload = yaml.safe_load((ROOT / "configs/data/source-identity-policy.yaml").read_text(encoding="utf-8"))

    validate_policy_payload(payload)
    assert payload["version"] == "source-identity-policy-0.1.0"


def test_fixture_identity_is_allowed_only_in_fixture_mode():
    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(fixture_metadata(), policy)

    assert result.status == "FIXTURE_ONLY"
    assert result.mode == "FIXTURE"
    assert result.production_allowed is False
    assert "PRODUCTION_DATASET_CONSTRUCTION" in result.blocked_actions


def test_real_source_rejects_fixture_canonical_symbol():
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "TR_FIXTURE_SPY"

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "FIXTURE_SYMBOL_FORBIDDEN_FOR_REAL_SOURCE" in result.blocked_reasons


def test_real_source_rejects_fixture_source_id_fragment():
    metadata = fixture_metadata()
    metadata["source_id"] = "real-fixture-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "FIXTURE_IDENTIFIER_FRAGMENT_FORBIDDEN" in result.blocked_reasons


def test_real_source_rejects_unset_metadata_sentinels():
    metadata = yaml.safe_load(
        (ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml").read_text(encoding="utf-8")
    )

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "UNSET_REAL_SOURCE_METADATA" in result.blocked_reasons


def test_real_source_requires_human_decision_reference():
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["raw_symbol"] = "SPY"
    metadata.pop("human_decision_ref", None)

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "MISSING_HUMAN_DECISION_REF" in result.blocked_reasons


def test_real_source_decision_reference_must_stay_under_decisions():
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/status/not-a-decision.md"

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "HUMAN_DECISION_REF_OUTSIDE_DECISIONS" in result.blocked_reasons


def test_real_source_decision_reference_must_exist():
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "HUMAN_DECISION_REF_NOT_FOUND" in result.blocked_reasons


def test_real_source_decision_reference_cannot_escape_decisions():
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/decisions/../inbox/human/not-a-decision.md"

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy)

    assert result.status == "BLOCKED"
    assert "HUMAN_DECISION_REF_OUTSIDE_DECISIONS" in result.blocked_reasons


def test_real_source_decision_reference_must_be_a_record(tmp_path: Path):
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"
    decision_path = tmp_path / "agent-exchange/decisions/example.md"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text("Approver:\nCreated at:\nScope:\nDecision:\n", encoding="utf-8")

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy, project_root=tmp_path)

    assert result.status == "BLOCKED"
    assert "HUMAN_DECISION_REF_NOT_A_RECORD" in result.blocked_reasons


def test_real_source_identity_contract_does_not_approve_production(tmp_path: Path):
    metadata = fixture_metadata()
    metadata["source_id"] = "real-ohlcv-spy-1m"
    metadata["canonical_symbol"] = "SPY.US"
    metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"
    decision_path = tmp_path / "agent-exchange/decisions/example.md"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        "\n".join(
            [
                "Approver: Human Data Owner",
                "Created at: 2026-08-31T19:20:00Z",
                "Scope: First real OHLCV intake review only",
                "Decision: NOT_APPROVED",
                "Evidence: Local operator note; no production approval",
            ]
        ),
        encoding="utf-8",
    )

    policy = load_source_identity_policy(ROOT / "configs/data/source-identity-policy.yaml")
    result = validate_source_identity(metadata, policy, project_root=tmp_path)

    assert result.status == "REAL_SOURCE_PENDING_HUMAN_DECISION"
    assert result.production_allowed is False
    assert "PRODUCTION_DATASET_CONSTRUCTION" in result.blocked_actions
