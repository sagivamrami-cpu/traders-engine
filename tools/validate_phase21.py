from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json, validate_json_payload

SCHEMA_PATH = ROOT / "schemas/databento_gc_vendor_preflight.schema.json"
POLICY_PATH = ROOT / "configs/data/databento-gc-vendor-preflight.yaml"
DECISIONS_PATH = ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"
CONTRACT_STYPE_DECISION_TEMPLATE_PATH = ROOT / "configs/data/databento-gc-contract-stype-decision-template.yaml"
CONTRACT_STYPE_DECISION_SCHEMA_PATH = ROOT / "schemas/databento_gc_contract_stype_decision.schema.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase20.py")])
    _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/research/test_databento_vendor_preflight.py",
            "tests/research/test_databento_contract_stype_decision.py",
            "-q",
        ]
    )

    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))
    Draft202012Validator.check_schema(load_json(CONTRACT_STYPE_DECISION_SCHEMA_PATH))

    offline_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/preflight_databento_gc_vendor.py"),
            "--policy",
            str(POLICY_PATH),
            "--offline",
        ]
    )
    offline_payload = json.loads(offline_result.stdout)
    validate_json_payload(SCHEMA_PATH, offline_payload)
    _require(
        offline_payload["status"] == "OFFLINE_PLAN_RECORDED_API_KEY_BLOCKED",
        "offline Databento preflight must remain API-key blocked",
    )
    _require(offline_payload["download_allowed"] is False, "offline Databento preflight must block downloads")
    _require(offline_payload["purchase_allowed"] is False, "offline Databento preflight must block purchases")
    _require(offline_payload["contract_identity_status"] == "UNDECLARED_PENDING_RESEARCH", "contract identity must stay pending")
    _require(offline_payload["stype_in_status"] == "RESEARCH_DECISION_PENDING", "stype_in must stay pending")
    _require(offline_payload["estimate_window_role"] == "SAMPLE_DAY_NOT_FULL_INTERVAL", "estimate window must be sample-only")
    _require(offline_payload["coverage_status"] == "NOT_PROVEN_SAMPLE_DAY_ONLY", "coverage must not be inferred from sample day")
    _require(offline_payload["mbo_era_status"] == "MBO_ERA_COVERAGE_REQUIRES_VENDOR_VERIFICATION", "MBO era coverage must stay unverified")
    _require("APPROVE_ORDER_FLOW_SOURCE" in offline_payload["blocked_actions"], "order-flow approval must remain blocked")
    _require("QUERY_OPTIONS_PARENT" in offline_payload["blocked_actions"], "options parent query must remain blocked")
    _require("PURCHASE_MBO_DATA" in offline_payload["blocked_actions"], "MBO purchase must remain blocked")
    _require("MAP_GC_TO_XAUUSD" in offline_payload["blocked_actions"], "GC to XAUUSD mapping must remain blocked")
    _require("MAP_GC_TO_GLD" in offline_payload["blocked_actions"], "GC to GLD mapping must remain blocked")
    _require("LOCAL_PATH_REDACTED" not in offline_result.stdout, "preflight output must not use local paths")
    _require("db-" not in offline_result.stdout, "preflight output must not leak Databento API keys")
    _require("READY" not in offline_payload["status"], "preflight status must not use READY")
    _require(
        "AVAILABLE"
        not in {
            offline_payload["dataset_status"],
            offline_payload["schemas_status"],
            offline_payload["symbol_resolution_status"],
        },
        "preflight metadata statuses must not use AVAILABLE",
    )

    missing_env = os.environ.copy()
    missing_env.pop("DATABENTO_API_KEY", None)
    missing_env["UNRELATED_SECRET"] = "db-validator-secret-must-not-leak"
    missing_key_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/preflight_databento_gc_vendor.py"),
            "--policy",
            str(POLICY_PATH),
            "--online-cost-estimate",
        ],
        env=missing_env,
        check=False,
    )
    _require(missing_key_result.returncode == 2, "online preflight without API key must exit 2")
    missing_key_payload = json.loads(missing_key_result.stdout)
    validate_json_payload(SCHEMA_PATH, missing_key_payload)
    _require(
        missing_key_payload["status"] == "BLOCKED_API_KEY_MISSING",
        "missing-key Databento preflight must use blocked status",
    )
    _require("db-validator-secret-must-not-leak" not in missing_key_result.stdout, "environment secrets must not leak")
    _require(missing_key_result.stderr == "", "missing-key preflight must not print stderr")

    contract_env = os.environ.copy()
    contract_env["DATABENTO_API_KEY"] = "db-validator-secret-must-not-leak"
    missing_contract_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/preflight_databento_gc_vendor.py"),
            "--policy",
            str(POLICY_PATH),
            "--online-cost-estimate",
        ],
        env=contract_env,
        check=False,
    )
    _require(missing_contract_result.returncode == 3, "online preflight with key must require contract/stype decision")
    missing_contract_payload = json.loads(missing_contract_result.stdout)
    validate_json_payload(SCHEMA_PATH, missing_contract_payload)
    _require(
        missing_contract_payload["status"] == "BLOCKED_CONTRACT_STYPE_DECISION_MISSING",
        "contract/stype decision must block online preflight",
    )
    _require("db-validator-secret-must-not-leak" not in missing_contract_result.stdout, "API key must not leak")
    _require(missing_contract_result.stderr == "", "missing-contract preflight must not print stderr")

    contract_template_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/validate_databento_gc_contract_stype_decision.py"),
            "--decision",
            str(CONTRACT_STYPE_DECISION_TEMPLATE_PATH),
        ]
    )
    contract_template_payload = json.loads(contract_template_result.stdout)
    validate_json_payload(CONTRACT_STYPE_DECISION_SCHEMA_PATH, contract_template_payload)
    _require(
        contract_template_payload["status"] == "OPEN_HUMAN_DECISION",
        "contract/stype template must remain an open human decision",
    )
    _require(
        contract_template_payload["approved_for_cost_preflight"] is False,
        "contract/stype template must not approve cost preflight",
    )

    readiness_result = _run(
        [
            sys.executable,
            str(ROOT / "tools/real_data_readiness.py"),
            "--decisions",
            str(DECISIONS_PATH),
        ]
    )
    readiness = json.loads(readiness_result.stdout)
    _require(readiness["status"] == "BLOCKED", "readiness with GC decisions must remain blocked")
    _require(readiness["satisfied_count"] == 6, "GC decisions must satisfy exactly six readiness items")
    _require(readiness["open_count"] == 1, "only options decision must remain open/deferred")
    open_items = {
        item["item_id"]
        for item in readiness["required_items"]
        if item["status"] == "OPEN_HUMAN_DECISION"
    }
    _require("ORDER_FLOW_SOURCE_DECISION" not in open_items, "order-flow decision must be approved")
    _require("OPTIONS_SOURCE_DECISION" in open_items, "options decision must remain open/deferred")

    print("Phase 21 artifacts validated")


if __name__ == "__main__":
    main()
