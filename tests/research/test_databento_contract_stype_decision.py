import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from trading_system.research.databento_contract_stype_decision import (
    apply_contract_stype_decision,
    load_databento_contract_stype_decision,
)
from trading_system.research.databento_vendor_preflight import (
    build_online_databento_vendor_preflight,
    load_databento_vendor_preflight_policy,
)

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "configs/data/databento-gc-contract-stype-decision-template.yaml"
POLICY_PATH = ROOT / "configs/data/databento-gc-vendor-preflight.yaml"
SCHEMA_PATH = ROOT / "schemas/databento_gc_contract_stype_decision.schema.json"
PREFLIGHT_SCHEMA_PATH = ROOT / "schemas/databento_gc_vendor_preflight.schema.json"


class FakeMetadata:
    def get_dataset(self, dataset):
        return {"dataset": dataset}

    def list_schemas(self, dataset):
        return ["trades", "mbp-10", "mbo"]

    def get_cost(self, *, dataset, start, end, symbols, schema, stype_in):
        return {"trades": 1.0, "mbp-10": 2.0}[schema]


class FakeSymbology:
    def __init__(self):
        self.resolve_calls = []

    def resolve(self, *, dataset, symbols, stype_in, stype_out, start_date, end_date):
        self.resolve_calls.append(
            {
                "dataset": dataset,
                "symbols": symbols,
                "stype_in": stype_in,
                "stype_out": stype_out,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return {"result": {symbol: [] for symbol in symbols}}


class FakeDatabentoClient:
    def __init__(self):
        self.metadata = FakeMetadata()
        self.symbology = FakeSymbology()


def validate_payload(payload: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def validate_preflight_payload(payload: dict) -> None:
    schema = json.loads(PREFLIGHT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def write_decision(tmp_path: Path, overrides: dict) -> Path:
    raw = yaml.safe_load(TEMPLATE_PATH.read_text(encoding="utf-8"))
    raw.update(overrides)
    path = tmp_path / "contract-stype-decision.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def approved_parent_decision(tmp_path: Path) -> Path:
    return write_decision(
        tmp_path,
        {
            "status": "APPROVED_FOR_COST_PREFLIGHT_ONLY",
            "approved_by": "Human Data Owner",
            "decided_at": "2026-09-01T00:20:00Z",
            "evidence": ["agent-exchange/decisions/example-human-contract-stype.md"],
            "selected_mode": "parent_futures",
            "selected_symbols": ["GC.FUT"],
        },
    )


def approved_continuous_decision(tmp_path: Path) -> Path:
    return write_decision(
        tmp_path,
        {
            "status": "APPROVED_FOR_COST_PREFLIGHT_ONLY",
            "approved_by": "Human Data Owner",
            "decided_at": "2026-09-01T00:20:00Z",
            "evidence": ["agent-exchange/decisions/example-human-contract-stype.md"],
            "selected_mode": "continuous_front_month",
            "selected_symbols": ["GC.v.0"],
        },
    )


def test_open_template_validates_but_does_not_approve_online_cost_preflight():
    decision = load_databento_contract_stype_decision(TEMPLATE_PATH)
    payload = decision.to_payload()

    validate_payload(payload)
    assert payload["status"] == "OPEN_HUMAN_DECISION"
    assert payload["approved_for_cost_preflight"] is False
    assert payload["selected_mode"] is None
    assert payload["selected_symbols"] == []
    assert payload["purchase_allowed"] is False
    assert payload["download_allowed"] is False
    assert "CONTRACT_STYPE_DECISION_OPEN" in payload["blocked_reasons"]


def test_approved_parent_decision_applies_selected_symbols_to_cost_policy(tmp_path: Path):
    decision = load_databento_contract_stype_decision(approved_parent_decision(tmp_path))
    policy = load_databento_vendor_preflight_policy(POLICY_PATH)
    client = FakeDatabentoClient()

    validate_payload(decision.to_payload())
    assert decision.approved_for_cost_preflight is True
    updated_policy = apply_contract_stype_decision(policy, decision)
    payload = build_online_databento_vendor_preflight(
        updated_policy,
        client=client,
        created_at=decision.decided_at,
        api_key_present=True,
    ).to_payload()

    validate_preflight_payload(payload)
    assert client.symbology.resolve_calls == [
        {
            "dataset": "GLBX.MDP3",
            "symbols": ["GC.FUT"],
            "stype_in": "parent",
            "stype_out": "instrument_id",
            "start_date": "2026-08-04",
            "end_date": "2026-08-05",
        }
    ]
    assert {tuple(request["symbols"]) for request in payload["estimated_requests"]} == {("GC",)}
    assert {request["stype_in"] for request in payload["estimated_requests"]} == {"raw_symbol"}
    assert {tuple(request["query_symbols"]) for request in payload["estimated_requests"]} == {("GC.FUT",)}
    assert {request["query_stype_in"] for request in payload["estimated_requests"]} == {"parent"}
    assert payload["stype_in_status"] == "COST_PREFLIGHT_QUERY_STYPE_RECORDED_NOT_IDENTITY"
    assert payload["purchase_allowed"] is False
    assert payload["training_allowed"] is False


def test_approved_continuous_decision_validates_online_preflight_payload(tmp_path: Path):
    decision = load_databento_contract_stype_decision(approved_continuous_decision(tmp_path))
    policy = load_databento_vendor_preflight_policy(POLICY_PATH)
    client = FakeDatabentoClient()

    updated_policy = apply_contract_stype_decision(policy, decision)
    payload = build_online_databento_vendor_preflight(
        updated_policy,
        client=client,
        created_at=decision.decided_at,
        api_key_present=True,
    ).to_payload()

    validate_preflight_payload(payload)
    assert {tuple(request["symbols"]) for request in payload["estimated_requests"]} == {("GC",)}
    assert {request["stype_in"] for request in payload["estimated_requests"]} == {"raw_symbol"}
    assert {tuple(request["query_symbols"]) for request in payload["estimated_requests"]} == {("GC.v.0",)}
    assert {request["query_stype_in"] for request in payload["estimated_requests"]} == {"continuous"}
    assert client.symbology.resolve_calls[0]["stype_in"] == "continuous"


def test_approved_decision_rejects_alias_symbols_and_unknown_modes(tmp_path: Path):
    for bad_symbol in ("XAUUSD", "GLD", "ES", "CL.FUT", "NQ.v.0", "GC", "GC.OPT"):
        path = write_decision(
            tmp_path,
            {
                "status": "APPROVED_FOR_COST_PREFLIGHT_ONLY",
                "approved_by": "Human Data Owner",
                "decided_at": "2026-09-01T00:20:00Z",
                "evidence": ["agent-exchange/decisions/example-human-contract-stype.md"],
                "selected_mode": "parent_futures",
                "selected_symbols": [bad_symbol],
            },
        )
        with pytest.raises(ValueError, match="Selected symbols are not valid for selected mode"):
            load_databento_contract_stype_decision(path)

    unknown_mode_path = write_decision(
        tmp_path,
        {
            "status": "APPROVED_FOR_COST_PREFLIGHT_ONLY",
            "approved_by": "Human Data Owner",
            "decided_at": "2026-09-01T00:20:00Z",
            "evidence": ["agent-exchange/decisions/example-human-contract-stype.md"],
            "selected_mode": "invented_mode",
            "selected_symbols": ["GC.FUT"],
        },
    )
    with pytest.raises(ValueError, match="Unknown Databento contract/stype mode"):
        load_databento_contract_stype_decision(unknown_mode_path)


def test_approved_decision_rejects_mode_symbol_mismatches(tmp_path: Path):
    cases = [
        ("dated_raw_symbol", "GC.FUT"),
        ("dated_raw_symbol", "GC.v.0"),
        ("parent_futures", "GCZ6"),
        ("parent_futures", "GC.v.0"),
        ("continuous_front_month", "GCZ6"),
        ("continuous_front_month", "GC.FUT"),
    ]
    for selected_mode, selected_symbol in cases:
        path = write_decision(
            tmp_path,
            {
                "status": "APPROVED_FOR_COST_PREFLIGHT_ONLY",
                "approved_by": "Human Data Owner",
                "decided_at": "2026-09-01T00:20:00Z",
                "evidence": ["agent-exchange/decisions/example-human-contract-stype.md"],
                "selected_mode": selected_mode,
                "selected_symbols": [selected_symbol],
            },
        )

        with pytest.raises(ValueError, match="Selected symbols are not valid for selected mode"):
            load_databento_contract_stype_decision(path)


def test_approved_dated_decision_accepts_gc_contract_shape(tmp_path: Path):
    decision = load_databento_contract_stype_decision(
        write_decision(
            tmp_path,
            {
                "status": "APPROVED_FOR_COST_PREFLIGHT_ONLY",
                "approved_by": "Human Data Owner",
                "decided_at": "2026-09-01T00:20:00Z",
                "evidence": ["agent-exchange/decisions/example-human-contract-stype.md"],
                "selected_mode": "dated_raw_symbol",
                "selected_symbols": ["GCZ6"],
            },
        )
    )

    validate_payload(decision.to_payload())
    assert decision.stype_in == "raw_symbol"
    assert decision.selected_symbols == ("GCZ6",)


def test_approved_decision_requires_human_metadata_and_symbols(tmp_path: Path):
    for missing_field in ("approved_by", "decided_at", "evidence", "selected_symbols"):
        overrides = {
            "status": "APPROVED_FOR_COST_PREFLIGHT_ONLY",
            "approved_by": "Human Data Owner",
            "decided_at": "2026-09-01T00:20:00Z",
            "evidence": ["agent-exchange/decisions/example-human-contract-stype.md"],
            "selected_mode": "parent_futures",
            "selected_symbols": ["GC.FUT"],
        }
        overrides[missing_field] = [] if missing_field in {"evidence", "selected_symbols"} else None
        with pytest.raises(ValueError, match="Approved contract/stype decisions require"):
            load_databento_contract_stype_decision(write_decision(tmp_path, overrides))


def test_approved_decision_requires_timezone_aware_decided_at(tmp_path: Path):
    with pytest.raises(ValueError, match="decided_at must include timezone"):
        load_databento_contract_stype_decision(
            write_decision(
                tmp_path,
                {
                    "status": "APPROVED_FOR_COST_PREFLIGHT_ONLY",
                    "approved_by": "Human Data Owner",
                    "decided_at": "2026-09-01T00:20:00",
                    "evidence": ["agent-exchange/decisions/example-human-contract-stype.md"],
                    "selected_mode": "parent_futures",
                    "selected_symbols": ["GC.FUT"],
                },
            )
        )


def test_contract_stype_decision_cli_outputs_sanitized_payload(tmp_path: Path):
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_databento_gc_contract_stype_decision.py",
            "--decision",
            str(approved_parent_decision(tmp_path)),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["status"] == "APPROVED_FOR_COST_PREFLIGHT_ONLY"
    assert str(tmp_path) not in result.stdout
    assert "db-" not in result.stdout


def test_online_preflight_cli_validates_contract_stype_before_client_creation(tmp_path: Path):
    env = {"DATABENTO_API_KEY": "db-this-key-must-not-leak"}

    result = subprocess.run(
        [
            sys.executable,
            "tools/preflight_databento_gc_vendor.py",
            "--policy",
            "configs/data/databento-gc-vendor-preflight.yaml",
            "--contract-stype-decision",
            str(TEMPLATE_PATH),
            "--online-cost-estimate",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 4
    assert result.stdout == ""
    assert json.loads(result.stderr) == {
        "error": "BLOCKED_CONTRACT_STYPE_DECISION_NOT_APPROVED",
        "status": "BLOCKED",
    }
    assert "db-this-key-must-not-leak" not in result.stderr
