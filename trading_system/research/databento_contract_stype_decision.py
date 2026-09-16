from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json
from trading_system.features.contracts import utc_iso
from trading_system.research.databento_vendor_preflight import (
    BLOCKED_ACTIONS as PREFLIGHT_BLOCKED_ACTIONS,
    CANONICAL_SYMBOL,
    DATASET,
    DatabentoVendorPreflightPolicy,
    load_databento_vendor_preflight_policy_from_object,
)

DECISION_VERSION = "databento-gc-contract-stype-decision-0.1.0"
APPROVED_STATUS = "APPROVED_FOR_COST_PREFLIGHT_ONLY"
OPEN_STATUS = "OPEN_HUMAN_DECISION"
DECISION_SCOPE = "COST_PREFLIGHT_ONLY"
ALIAS_SYMBOLS = {"XAUUSD", "GLD"}
MODE_TO_STYPE = {
    "dated_raw_symbol": "raw_symbol",
    "parent_futures": "parent",
    "continuous_front_month": "continuous",
}
BLOCKED_ACTIONS = PREFLIGHT_BLOCKED_ACTIONS


@dataclass(frozen=True)
class DatabentoContractStypeDecision:
    status: str
    decision_scope: str
    canonical_symbol: str
    dataset: str
    selected_mode: str | None
    selected_symbols: tuple[str, ...]
    approved_by: str | None
    decided_at: datetime | None
    evidence: tuple[str, ...]
    blocked_reasons: tuple[str, ...]

    @property
    def stype_in(self) -> str | None:
        if self.selected_mode is None:
            return None
        return MODE_TO_STYPE[self.selected_mode]

    @property
    def approved_for_cost_preflight(self) -> bool:
        return self.status == APPROVED_STATUS

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_version": DECISION_VERSION,
            "status": self.status,
            "decision_scope": self.decision_scope,
            "canonical_symbol": self.canonical_symbol,
            "dataset": self.dataset,
            "approved_for_cost_preflight": self.approved_for_cost_preflight,
            "approved_by": self.approved_by,
            "decided_at": utc_iso(self.decided_at) if self.decided_at else None,
            "evidence": list(self.evidence),
            "selected_mode": self.selected_mode,
            "selected_symbols": list(self.selected_symbols),
            "stype_in": self.stype_in,
            "purchase_allowed": False,
            "download_allowed": False,
            "training_allowed": False,
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(self.blocked_reasons),
        }


def load_databento_contract_stype_decision(path: Path) -> DatabentoContractStypeDecision:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    decision = databento_contract_stype_decision_from_mapping(raw)
    schema_path = Path(__file__).resolve().parents[2] / "schemas/databento_gc_contract_stype_decision.schema.json"
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(decision.to_payload())
    return decision


def databento_contract_stype_decision_from_mapping(raw: Any) -> DatabentoContractStypeDecision:
    if not isinstance(raw, dict):
        raise ValueError("Databento contract/stype decision must be a mapping")
    status = str(raw.get("status", "")).strip()
    selected_mode_raw = raw.get("selected_mode")
    selected_mode = str(selected_mode_raw).strip() if selected_mode_raw else None
    selected_symbols = tuple(str(symbol).strip() for symbol in raw.get("selected_symbols", []) if str(symbol).strip())
    decided_at = _parse_decided_at(raw.get("decided_at"))
    decision = DatabentoContractStypeDecision(
        status=status,
        decision_scope=str(raw.get("decision_scope", "")).strip(),
        canonical_symbol=str(raw.get("canonical_symbol", "")).strip(),
        dataset=str(raw.get("dataset", "")).strip(),
        selected_mode=selected_mode,
        selected_symbols=selected_symbols,
        approved_by=_clean_optional(raw.get("approved_by")),
        decided_at=decided_at,
        evidence=tuple(str(item).strip() for item in raw.get("evidence", []) if str(item).strip()),
        blocked_reasons=_blocked_reasons(status),
    )
    _validate_decision(decision)
    return decision


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _parse_decided_at(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("decided_at must include timezone")
    return parsed


def _blocked_reasons(status: str) -> tuple[str, ...]:
    if status == OPEN_STATUS:
        return ("CONTRACT_STYPE_DECISION_OPEN", "PURCHASE_REQUIRES_HUMAN_APPROVAL")
    return ("PURCHASE_REQUIRES_HUMAN_APPROVAL",)


def _validate_decision(decision: DatabentoContractStypeDecision) -> None:
    if decision.decision_scope != DECISION_SCOPE:
        raise ValueError("Contract/stype decision scope must be COST_PREFLIGHT_ONLY")
    if decision.canonical_symbol != CANONICAL_SYMBOL:
        raise ValueError("Contract/stype decision must use GC canonical symbol")
    if decision.dataset != DATASET:
        raise ValueError("Contract/stype decision must use GLBX.MDP3")
    if decision.status not in {OPEN_STATUS, APPROVED_STATUS}:
        raise ValueError("Unknown Databento contract/stype decision status")
    if decision.selected_mode is not None and decision.selected_mode not in MODE_TO_STYPE:
        raise ValueError("Unknown Databento contract/stype mode")
    if decision.status == OPEN_STATUS:
        if any(
            (
                decision.selected_mode,
                decision.selected_symbols,
                decision.approved_by,
                decision.decided_at,
                decision.evidence,
            )
        ):
            raise ValueError("Open contract/stype decisions must not carry approval fields")
        return
    if not all(
        (
            decision.selected_mode,
            decision.selected_symbols,
            decision.approved_by,
            decision.decided_at,
            decision.evidence,
        )
    ):
        raise ValueError("Approved contract/stype decisions require human metadata and selected symbols")
    if not _selected_symbols_match_mode(decision.selected_mode, decision.selected_symbols):
        raise ValueError("Selected symbols are not valid for selected mode")


def _selected_symbols_match_mode(selected_mode: str | None, selected_symbols: tuple[str, ...]) -> bool:
    if any(symbol in ALIAS_SYMBOLS for symbol in selected_symbols):
        return False
    if selected_mode == "dated_raw_symbol":
        return all(_is_gc_dated_contract(symbol) for symbol in selected_symbols)
    if selected_mode == "parent_futures":
        return selected_symbols == ("GC.FUT",)
    if selected_mode == "continuous_front_month":
        return all(symbol.startswith("GC.v.") and symbol[5:].isdigit() for symbol in selected_symbols)
    return False


def _is_gc_dated_contract(symbol: str) -> bool:
    if len(symbol) < 4:
        return False
    month = symbol[2]
    year = symbol[3:]
    return symbol.startswith("GC") and month in "FGHJKMNQUVXZ" and year.isdigit() and 1 <= len(year) <= 2


def apply_contract_stype_decision(
    policy: DatabentoVendorPreflightPolicy,
    decision: DatabentoContractStypeDecision,
) -> DatabentoVendorPreflightPolicy:
    if not decision.approved_for_cost_preflight:
        raise ValueError("Contract/stype decision is not approved for cost preflight")
    updated_requests = tuple(
        replace(
            request,
            query_symbols=decision.selected_symbols,
            query_stype_in=decision.stype_in,
        )
        for request in policy.requests
    )
    return load_databento_vendor_preflight_policy_from_object(replace(policy, requests=updated_requests))
