import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from trading_system.research.databento_vendor_preflight import (
    build_missing_api_key_databento_vendor_preflight,
    build_missing_contract_stype_decision_databento_vendor_preflight,
    build_offline_databento_vendor_preflight,
    build_online_databento_vendor_preflight,
    load_databento_vendor_preflight_policy_from_object,
    load_databento_vendor_preflight_policy,
    wrap_databento_metadata_client,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs/data/databento-gc-vendor-preflight.yaml"
SCHEMA_PATH = ROOT / "schemas/databento_gc_vendor_preflight.schema.json"
CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)


class FakeMetadata:
    def __init__(self):
        self.calls = []

    def get_dataset(self, dataset):
        self.calls.append(("get_dataset", dataset))
        return {"dataset": dataset, "publisher": "CME Globex"}

    def list_schemas(self, dataset):
        self.calls.append(("list_schemas", dataset))
        return ["definition", "trades", "mbp-10", "mbo"]

    def get_cost(self, *, dataset, start, end, symbols, schema, stype_in):
        self.calls.append(("get_cost", dataset, start, end, tuple(symbols), schema, stype_in))
        return {
            "trades": 1.25,
            "mbp-10": 4.5,
            "mbo": 19.75,
        }[schema]


class FailingTimeseries:
    def __getattr__(self, name):
        raise AssertionError(f"timeseries.{name} must not be used by preflight")


class FailingBatch:
    def __getattr__(self, name):
        raise AssertionError(f"batch.{name} must not be used by preflight")


class FailingLive:
    def __getattr__(self, name):
        raise AssertionError(f"live.{name} must not be used by preflight")


class FakeSymbology:
    def __init__(self):
        self.calls = []

    def resolve(self, *, dataset, symbols, stype_in, stype_out, start_date, end_date):
        self.calls.append((dataset, tuple(symbols), stype_in, stype_out, start_date, end_date))
        return {
            "result": {
                symbol: [
                    {
                        "s": symbol,
                        "d0": start_date,
                        "d1": end_date,
                        "instrument_id": 12345,
                    }
                ]
                for symbol in symbols
            }
        }


class FakeDatabentoClient:
    def __init__(self):
        self.metadata = FakeMetadata()
        self.symbology = FakeSymbology()
        self.timeseries = FailingTimeseries()
        self.batch = FailingBatch()
        self.live = FailingLive()


class ExpensiveMetadata(FakeMetadata):
    def get_cost(self, *, dataset, start, end, symbols, schema, stype_in):
        self.calls.append(("get_cost", dataset, start, end, tuple(symbols), schema, stype_in))
        return 26.0


class MissingSchemaMetadata(FakeMetadata):
    def list_schemas(self, dataset):
        self.calls.append(("list_schemas", dataset))
        return ["definition", "trades", "mbp-10"]


class MissingTradesSchemaMetadata(FakeMetadata):
    def list_schemas(self, dataset):
        self.calls.append(("list_schemas", dataset))
        return ["definition", "mbp-10", "mbo"]


class RaisingCostMetadata(FakeMetadata):
    def get_cost(self, *, dataset, start, end, symbols, schema, stype_in):
        self.calls.append(("get_cost", dataset, start, end, tuple(symbols), schema, stype_in))
        raise RuntimeError("vendor error that must be sanitized")


class CustomMetadataClient(FakeDatabentoClient):
    def __init__(self, metadata):
        super().__init__()
        self.metadata = metadata


def validate_payload(payload: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def policy():
    return load_databento_vendor_preflight_policy(POLICY_PATH)


def test_offline_preflight_blocks_paid_actions_and_keeps_options_parent_unqueried():
    payload = build_offline_databento_vendor_preflight(policy(), created_at=CREATED_AT).to_payload()

    validate_payload(payload)
    assert payload["status"] == "OFFLINE_PLAN_RECORDED_API_KEY_BLOCKED"
    assert payload["api_key_source"] == "ENV:DATABENTO_API_KEY"
    assert payload["api_key_present"] is False
    assert payload["download_allowed"] is False
    assert payload["purchase_allowed"] is False
    assert payload["timeseries_get_range_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["contract_identity_status"] == "UNDECLARED_PENDING_RESEARCH"
    assert payload["stype_in_status"] == "RESEARCH_DECISION_PENDING"
    assert payload["estimate_window_role"] == "SAMPLE_DAY_NOT_FULL_INTERVAL"
    assert payload["coverage_status"] == "NOT_PROVEN_SAMPLE_DAY_ONLY"
    assert payload["mbo_era_status"] == "MBO_ERA_COVERAGE_REQUIRES_VENDOR_VERIFICATION"
    assert payload["options_parent"]["status"] == "UNCONFIRMED_DO_NOT_QUERY"
    assert payload["options_parent"]["queried"] is False
    assert {request["schema"] for request in payload["estimated_requests"]} == {
        "trades",
        "mbp-10",
        "mbo",
    }
    assert all(request["cost_usd"] is None for request in payload["estimated_requests"])
    assert all(request["purchase_candidate"] is False for request in payload["estimated_requests"])
    assert all(
        request["symbol_identity_status"] == "AMBIGUOUS_NOT_A_DATED_CONTRACT"
        for request in payload["estimated_requests"]
    )
    assert "API_KEY_NOT_USED_OFFLINE" in payload["blocked_reasons"]
    assert "LIVE_TRADING" in payload["blocked_actions"]
    assert "APPROVE_ORDER_FLOW_SOURCE" in payload["blocked_actions"]
    assert "QUERY_OPTIONS_PARENT" in payload["blocked_actions"]
    assert "MAP_GC_TO_XAUUSD" in payload["blocked_actions"]
    serialized = json.dumps(payload, sort_keys=True)
    assert "db-" not in serialized
    assert str(ROOT) not in serialized
    assert "READY" not in payload["status"]
    assert "AVAILABLE" not in {
        payload["dataset_status"],
        payload["schemas_status"],
        payload["symbol_resolution_status"],
    }


def test_online_preflight_uses_only_metadata_symbology_and_cost_estimates():
    fake_client = FakeDatabentoClient()

    payload = build_online_databento_vendor_preflight(
        policy(),
        client=fake_client,
        created_at=CREATED_AT,
        api_key_present=True,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "COST_ESTIMATES_RECORDED_PURCHASE_BLOCKED"
    assert payload["api_key_present"] is True
    assert payload["dataset_status"] == "METADATA_RETURNED_NOT_APPROVED"
    assert payload["schemas_status"] == "METADATA_RETURNED_NOT_APPROVED"
    assert payload["symbol_resolution_status"] == "SYMBOL_METADATA_RETURNED_IDENTITY_UNCONFIRMED"
    assert payload["contract_identity_status"] == "UNDECLARED_PENDING_RESEARCH"
    assert payload["stype_in_status"] == "RESEARCH_DECISION_PENDING"
    assert [request["cost_usd"] for request in payload["estimated_requests"]] == [1.25, 4.5, None]
    assert [
        request["availability_status"] for request in payload["estimated_requests"]
    ] == [
        "COST_ESTIMATE_RECORDED_NOT_A_PURCHASE_QUOTE",
        "COST_ESTIMATE_RECORDED_NOT_A_PURCHASE_QUOTE",
        "REFERENCE_ONLY_NOT_A_PURCHASE_CANDIDATE",
    ]
    assert all(request["purchase_candidate"] is False for request in payload["estimated_requests"])
    mbo_request = next(request for request in payload["estimated_requests"] if request["schema"] == "mbo")
    assert "MBO_REFERENCE_ONLY_NOT_A_PURCHASE_CANDIDATE" in mbo_request["blocked_reasons"]
    assert "READY" not in payload["status"]
    assert len(fake_client.symbology.calls) == 1
    assert all(call[0] in {"get_dataset", "list_schemas", "get_cost"} for call in fake_client.metadata.calls)
    assert not any(call[0] == "get_cost" and call[5] == "mbo" for call in fake_client.metadata.calls)
    assert "PURCHASE_REQUIRES_HUMAN_APPROVAL" in payload["blocked_reasons"]


def test_online_preflight_blocks_costs_above_policy_cap():
    payload = build_online_databento_vendor_preflight(
        policy(),
        client=CustomMetadataClient(ExpensiveMetadata()),
        created_at=CREATED_AT,
        api_key_present=True,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "COST_EXCEEDS_POLICY_LIMIT" in payload["blocked_reasons"]
    assert all(
        request["availability_status"] == "BLOCKED_COST_EXCEEDS_POLICY_LIMIT"
        for request in payload["estimated_requests"]
        if request["schema"] != "mbo"
    )


def test_online_preflight_blocks_unavailable_schema_without_cost_call():
    metadata = MissingTradesSchemaMetadata()

    payload = build_online_databento_vendor_preflight(
        policy(),
        client=CustomMetadataClient(metadata),
        created_at=CREATED_AT,
        api_key_present=True,
    ).to_payload()

    validate_payload(payload)
    trades_request = next(request for request in payload["estimated_requests"] if request["schema"] == "trades")
    assert payload["status"] == "BLOCKED"
    assert trades_request["availability_status"] == "BLOCKED_SCHEMA_UNSUPPORTED"
    assert "SCHEMA_NOT_AVAILABLE" in trades_request["blocked_reasons"]
    assert not any(call[0] == "get_cost" and call[5] == "trades" for call in metadata.calls)


def test_online_preflight_blocks_cost_estimate_failures_without_crashing():
    payload = build_online_databento_vendor_preflight(
        policy(),
        client=CustomMetadataClient(RaisingCostMetadata()),
        created_at=CREATED_AT,
        api_key_present=True,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "COST_ESTIMATE_FAILED" in payload["blocked_reasons"]
    assert all(
        request["availability_status"] == "BLOCKED_COST_ESTIMATE_FAILED"
        for request in payload["estimated_requests"]
        if request["schema"] != "mbo"
    )


def test_missing_api_key_report_is_sanitized_and_blocks_online_estimates(monkeypatch):
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)

    payload = build_missing_api_key_databento_vendor_preflight(policy(), created_at=CREATED_AT).to_payload()

    validate_payload(payload)
    assert payload["status"] == "BLOCKED_API_KEY_MISSING"
    assert payload["api_key_present"] is False
    assert payload["estimated_requests"][0]["cost_usd"] is None
    assert "API_KEY_ENV_MISSING" in payload["blocked_reasons"]
    assert "DATABENTO_API_KEY" in payload["api_key_source"]
    assert "db-" not in json.dumps(payload, sort_keys=True)


def test_missing_contract_stype_decision_blocks_online_estimates_even_with_api_key():
    payload = build_missing_contract_stype_decision_databento_vendor_preflight(
        policy(),
        created_at=CREATED_AT,
        api_key_present=True,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "BLOCKED_CONTRACT_STYPE_DECISION_MISSING"
    assert payload["api_key_present"] is True
    assert payload["dataset_status"] == "NOT_CHECKED_CONTRACT_STYPE_DECISION_MISSING"
    assert payload["symbol_resolution_status"] == "NOT_CHECKED_CONTRACT_STYPE_DECISION_MISSING"
    assert all(request["cost_usd"] is None for request in payload["estimated_requests"])
    assert "CONTRACT_STYPE_DECISION_MISSING" in payload["blocked_reasons"]
    assert "DATABENTO_LIVE_CALL_BLOCKED_UNTIL_CONTRACT_STYPE_DECISION" in payload["blocked_actions"]


def test_preflight_cli_online_mode_missing_key_exits_two_without_leaking_env(tmp_path):
    env = os.environ.copy()
    env.pop("DATABENTO_API_KEY", None)
    env["UNRELATED_SECRET"] = "db-this-value-must-not-leak"

    result = subprocess.run(
        [
            sys.executable,
            "tools/preflight_databento_gc_vendor.py",
            "--policy",
            "configs/data/databento-gc-vendor-preflight.yaml",
            "--online-cost-estimate",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["status"] == "BLOCKED_API_KEY_MISSING"
    assert "db-this-value-must-not-leak" not in result.stdout
    assert result.stderr == ""


def test_preflight_cli_online_mode_with_key_but_no_contract_stype_decision_exits_three():
    env = os.environ.copy()
    env["DATABENTO_API_KEY"] = "db-this-key-must-not-leak"

    result = subprocess.run(
        [
            sys.executable,
            "tools/preflight_databento_gc_vendor.py",
            "--policy",
            "configs/data/databento-gc-vendor-preflight.yaml",
            "--online-cost-estimate",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 3
    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["status"] == "BLOCKED_CONTRACT_STYPE_DECISION_MISSING"
    assert "db-this-key-must-not-leak" not in result.stdout
    assert result.stderr == ""


def test_preflight_cli_unexpected_errors_exit_one_with_sanitized_stderr(tmp_path):
    env = os.environ.copy()
    env["DATABENTO_API_KEY"] = "db-this-key-must-not-leak"
    missing_policy = tmp_path / "missing-policy.yaml"

    result = subprocess.run(
        [
            sys.executable,
            "tools/preflight_databento_gc_vendor.py",
            "--policy",
            str(missing_policy),
            "--online-cost-estimate",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    error_payload = json.loads(result.stderr)
    assert error_payload == {
        "error": "DATABENTO_PREFLIGHT_FAILED",
        "status": "BLOCKED",
    }
    assert "db-this-key-must-not-leak" not in result.stderr
    assert str(missing_policy) not in result.stderr
    assert "Traceback" not in result.stderr


def test_preflight_config_keeps_order_flow_and_options_as_separate_gates():
    current_policy = policy()

    assert current_policy.dataset == "GLBX.MDP3"
    assert current_policy.canonical_symbol == "GC"
    assert current_policy.options_parent.status == "UNCONFIRMED_DO_NOT_QUERY"
    assert current_policy.options_parent.candidate_symbols == ()
    assert current_policy.purchase_allowed is False
    assert current_policy.no_data_download is True
    assert current_policy.timeseries_get_range_allowed is False


def test_policy_rejects_xauusd_and_gld_alias_symbols():
    current_policy = policy()

    with pytest.raises(ValueError, match="GC canonical symbol"):
        load_databento_vendor_preflight_policy_from_object(
            replace(current_policy, canonical_symbol="XAUUSD")
        )
    for alias in ("XAUUSD", "GLD"):
        alias_requests = (
            replace(current_policy.requests[0], symbols=(alias,)),
            *current_policy.requests[1:],
        )
        with pytest.raises(ValueError, match="only preflight GC"):
            load_databento_vendor_preflight_policy_from_object(
                replace(current_policy, requests=alias_requests)
            )


def test_schema_rejects_alias_symbols_in_report_payload():
    payload = build_offline_databento_vendor_preflight(policy(), created_at=CREATED_AT).to_payload()
    payload["estimated_requests"][0]["symbols"] = ["XAUUSD"]

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(payload))

    assert errors


def test_schema_rejects_ready_available_estimated_and_unknown_purpose_payloads():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    available_payload = build_offline_databento_vendor_preflight(policy(), created_at=CREATED_AT).to_payload()
    available_payload["dataset_status"] = "AVAILABLE"
    assert list(validator.iter_errors(available_payload))

    estimated_payload = build_offline_databento_vendor_preflight(policy(), created_at=CREATED_AT).to_payload()
    estimated_payload["estimated_requests"][0]["availability_status"] = "ESTIMATED"
    assert list(validator.iter_errors(estimated_payload))

    unknown_purpose_payload = build_offline_databento_vendor_preflight(policy(), created_at=CREATED_AT).to_payload()
    unknown_purpose_payload["estimated_requests"][0]["purpose"] = "AD_HOC_VENDOR_PULL"
    assert list(validator.iter_errors(unknown_purpose_payload))


def test_safe_databento_wrapper_exposes_only_metadata_and_symbology():
    wrapped = wrap_databento_metadata_client(FakeDatabentoClient())

    assert wrapped.metadata.get_dataset("GLBX.MDP3") == {"dataset": "GLBX.MDP3", "publisher": "CME Globex"}
    assert wrapped.symbology is not None
    for forbidden_surface in ("timeseries", "batch", "live"):
        with pytest.raises(RuntimeError, match="not allowed"):
            getattr(wrapped, forbidden_surface)
