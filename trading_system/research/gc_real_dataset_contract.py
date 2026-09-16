from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.manifests import to_plain_data, validate_json_payload
from trading_system.features.contracts import utc_iso
from trading_system.research.readiness import DEFERRED_DECISION, load_real_data_decisions

CONTRACT_VERSION = "gc-real-dataset-contract-0.1.0"
MODE = "GC_REAL_DATASET_CONTRACT"
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/gc_real_dataset_contract.schema.json"
STATUS_BLOCKED = "BLOCKED"
STATUS_CONSTRUCTION_AUTHORIZED = "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED"
CONSTRUCTION_GATED_ACTIONS = ("BUILD_REAL_DATASET", "BUILD_ORDER_FLOW_FEATURES")


@dataclass(frozen=True)
class GcRealDatasetContractReport:
    contract_report_id: str
    created_at: datetime
    contract: dict[str, Any]
    blocked_reasons: tuple[str, ...]

    @property
    def construction_authorized(self) -> bool:
        """True only when every gate is closed, the contract enables construction, and
        every authorization record verified (see ``_authorization_blockers``)."""
        contract = self.contract
        return (
            not self.blocked_reasons
            and not list(contract.get("required_unsatisfied_gates", []))
            and contract.get("dataset_construction_allowed") is True
            and bool(contract.get("construction_authorized_by"))
        )

    def to_payload(self) -> dict[str, Any]:
        authorized = self.construction_authorized
        blocked_actions = list(self.contract["blocked_actions"])
        if not authorized:
            blocked_actions = _unique([*blocked_actions, *CONSTRUCTION_GATED_ACTIONS])
        payload = {
            "contract_report_id": self.contract_report_id,
            "contract_version": CONTRACT_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": STATUS_CONSTRUCTION_AUTHORIZED if authorized else STATUS_BLOCKED,
            "contract_id": self.contract["contract_id"],
            "canonical_symbol": self.contract["canonical_symbol"],
            "candidate_timeframe": self.contract["candidate_timeframe"],
            "timeframe_status": self.contract["timeframe_status"],
            "interval_semantics": self.contract["interval_semantics"],
            "source_decisions": self.contract["source_decisions"],
            "canonical_ohlcv_input": self.contract["canonical_ohlcv_input"],
            "canonical_order_flow_input": self.contract["canonical_order_flow_input"],
            "session_calendar": self.contract["session_calendar"],
            "bar_boundary": self.contract["bar_boundary"],
            "timestamp_role": self.contract["timestamp_role"],
            "available_at_policy": self.contract["available_at_policy"],
            "missing_bar_policy": self.contract["missing_bar_policy"],
            "roll_policy": self.contract["roll_policy"],
            "order_flow_era_map": self.contract["order_flow_era_map"],
            "cumulative_feature_policy": self.contract["cumulative_feature_policy"],
            "reference_inputs": self.contract["reference_inputs"],
            "macro_features": self.contract["macro_features"],
            "options_features": self.contract["options_features"],
            "label_contract": self.contract["label_contract"],
            "split_and_embargo_policy": self.contract["split_and_embargo_policy"],
            "dataset_identity": self.contract["dataset_identity"],
            "dataset_construction_allowed": authorized,
            "training_allowed": False,
            "construction_authorized_by": list(self.contract["construction_authorized_by"]) if authorized else [],
            "required_unsatisfied_gates": list(self.contract["required_unsatisfied_gates"]),
            "blocked_actions": list(blocked_actions),
            "allowed_next_actions": ["BUILD_IDENTIFIED_REAL_DATASET"] if authorized else [],
            "blocked_reasons": list(self.blocked_reasons),
        }
        validate_gc_real_dataset_contract_payload(payload)
        return payload


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def load_gc_real_dataset_contract(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected dataset contract YAML mapping")
    return to_plain_data(loaded)


def validate_gc_real_dataset_contract_payload(payload: dict[str, Any]) -> None:
    validate_json_payload(SCHEMA_PATH, payload)


def _decision_blockers(decisions_path: Path) -> list[str]:
    decisions = load_real_data_decisions(decisions_path)
    by_item = {decision.item_id: decision.decision for decision in decisions.decisions}
    blockers: list[str] = []
    if by_item.get("ORDER_FLOW_SOURCE_DECISION") in (DEFERRED_DECISION, "NOT_APPROVED"):
        blockers.append("ORDER_FLOW_SOURCE_DECISION_MUST_REMAIN_OPEN_FOR_CONTRACT_ONLY_PHASE")
    if by_item.get("OPTIONS_SOURCE_DECISION") != DEFERRED_DECISION:
        blockers.append("OPTIONS_SOURCE_DECISION_MUST_BE_DEFERRED_TO_V2")
    return blockers


def _authorization_blockers(contract: dict[str, Any], root: Path) -> list[str]:
    """D9-final: construction may be enabled only with every gate closed and at least one
    APPROVED human decision record under agent-exchange/decisions/ that binds the exact
    dataset_id of the identity manifest."""
    blockers: list[str] = []
    gates = list(contract.get("required_unsatisfied_gates", []))
    refs = [str(ref) for ref in contract.get("construction_authorized_by", [])]
    allowed = contract.get("dataset_construction_allowed")
    if allowed not in (True, False):
        blockers.append("DATASET_CONSTRUCTION_ALLOWED_MUST_BE_BOOLEAN")
    if allowed is True and gates:
        blockers.append("CONSTRUCTION_ENABLED_WHILE_GATES_UNSATISFIED")
    if allowed is True and not refs:
        blockers.append("CONSTRUCTION_ENABLED_WITHOUT_AUTHORIZATION_RECORD")
    if refs and allowed is not True:
        blockers.append("AUTHORIZATION_RECORDED_BUT_CONSTRUCTION_NOT_ENABLED")
    dataset_id = str(contract.get("dataset_identity", {}).get("dataset_id", ""))
    for ref in refs:
        if not ref.startswith("agent-exchange/decisions/"):
            blockers.append(f"AUTHORIZATION_REF_NOT_A_DECISION_RECORD:{ref}")
            continue
        record = root / ref
        if not record.is_file():
            blockers.append(f"AUTHORIZATION_RECORD_MISSING:{ref}")
            continue
        text = record.read_text(encoding="utf-8")
        if "Decision: APPROVED" not in text:
            blockers.append(f"AUTHORIZATION_RECORD_NOT_APPROVED:{ref}")
        if not dataset_id or dataset_id not in text:
            blockers.append(f"AUTHORIZATION_RECORD_DOES_NOT_BIND_DATASET_ID:{ref}")
    return blockers


def _contract_blockers(contract: dict[str, Any], root: Path) -> list[str]:
    blockers = list(contract.get("required_unsatisfied_gates", []))
    if contract.get("training_allowed") is not False:
        blockers.append("TRAINING_MUST_REMAIN_BLOCKED")
    blockers.extend(_authorization_blockers(contract, root))
    return [str(blocker) for blocker in blockers]


def build_gc_real_dataset_contract_report(
    contract_path: Path,
    decisions_path: Path,
    *,
    created_at: datetime,
    root: Path | None = None,
) -> GcRealDatasetContractReport:
    contract = load_gc_real_dataset_contract(contract_path)
    blocked_reasons = tuple(_unique([*_contract_blockers(contract, root or ROOT), *_decision_blockers(decisions_path)]))
    id_payload = {
        "created_at": utc_iso(created_at),
        "contract_id": contract.get("contract_id"),
        "contract_version": contract.get("contract_version"),
        "required_unsatisfied_gates": list(contract.get("required_unsatisfied_gates", [])),
        "blocked_reasons": list(blocked_reasons),
    }
    return GcRealDatasetContractReport(
        contract_report_id=_report_id(id_payload),
        created_at=created_at,
        contract=contract,
        blocked_reasons=blocked_reasons,
    )
