from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.databento_vendor_preflight import (
    API_KEY_ENV,
    build_missing_api_key_databento_vendor_preflight,
    build_missing_contract_stype_decision_databento_vendor_preflight,
    build_offline_databento_vendor_preflight,
    build_online_databento_vendor_preflight,
    create_databento_historical_client,
    load_databento_vendor_preflight_policy,
)
from trading_system.research.databento_contract_stype_decision import (
    apply_contract_stype_decision,
    load_databento_contract_stype_decision,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a safe Databento GC vendor preflight.")
    parser.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "configs/data/databento-gc-vendor-preflight.yaml",
    )
    parser.add_argument(
        "--contract-stype-decision",
        type=Path,
        default=None,
        help="Required for online cost estimates; must be an explicit human-reviewed contract/stype decision.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="Emit an offline blocked plan without API calls.")
    mode.add_argument(
        "--online-cost-estimate",
        action="store_true",
        help="Use Databento metadata and get_cost only. Does not download market data.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        policy = load_databento_vendor_preflight_policy(args.policy)
        created_at = datetime.now(UTC)
        if args.online_cost_estimate:
            if not os.environ.get(API_KEY_ENV):
                report = build_missing_api_key_databento_vendor_preflight(policy, created_at=created_at)
                print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
                return 2
            if args.contract_stype_decision is None:
                report = build_missing_contract_stype_decision_databento_vendor_preflight(
                    policy,
                    created_at=created_at,
                    api_key_present=True,
                )
                print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
                return 3
            decision = load_databento_contract_stype_decision(args.contract_stype_decision)
            if not decision.approved_for_cost_preflight:
                print(
                    json.dumps(
                        {
                            "error": "BLOCKED_CONTRACT_STYPE_DECISION_NOT_APPROVED",
                            "status": "BLOCKED",
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
                return 4
            policy = apply_contract_stype_decision(policy, decision)
            client = create_databento_historical_client(policy.api_key_env)
            report = build_online_databento_vendor_preflight(
                policy,
                client=client,
                created_at=created_at,
                api_key_present=True,
            )
        else:
            report = build_offline_databento_vendor_preflight(policy, created_at=created_at)
        print(json.dumps(report.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    except Exception:
        error_payload = {
            "error": "DATABENTO_PREFLIGHT_FAILED",
            "status": "BLOCKED",
        }
        print(json.dumps(error_payload, ensure_ascii=True, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
