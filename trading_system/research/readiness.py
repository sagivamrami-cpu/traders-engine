from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.features.contracts import utc_iso

REPORT_VERSION = "real-data-readiness-report-0.3.0"
DECISIONS_VERSION = "real-data-decisions-0.1.0"

APPROVED_DECISION = "APPROVED"
NOT_APPROVED_DECISION = "NOT_APPROVED"
DEFERRED_DECISION = "DEFERRED"
_DECISION_VALUES = (APPROVED_DECISION, NOT_APPROVED_DECISION, DEFERRED_DECISION)
_FORBIDDEN_EVIDENCE_MARKERS = ("fixture", "synthetic")


@dataclass(frozen=True)
class RealDataDecision:
    item_id: str
    decision: str
    approver: str
    decided_at: str
    scope: str
    evidence: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "approver": self.approver,
            "decided_at": self.decided_at,
            "scope": self.scope,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class RealDataDecisionFile:
    version: str
    decisions: tuple[RealDataDecision, ...]


@dataclass(frozen=True)
class RealDataReadinessItem:
    item_id: str
    label: str
    status: str
    owner: str
    required_before: str
    decision: RealDataDecision | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "item_id": self.item_id,
            "label": self.label,
            "status": self.status,
            "owner": self.owner,
            "required_before": self.required_before,
        }
        if self.decision is not None:
            payload["decision"] = self.decision.to_payload()
        return payload


@dataclass(frozen=True)
class RealDataReadinessChecklist:
    version: str
    required_items: tuple[RealDataReadinessItem, ...]
    blocked_actions: tuple[str, ...]


@dataclass(frozen=True)
class RealDataReadinessReport:
    report_id: str
    created_at: datetime
    status: str
    checklist_version: str
    decisions_version: str | None
    required_items: tuple[RealDataReadinessItem, ...]
    blocked_actions: tuple[str, ...]
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        required_count = len(self.required_items)
        satisfied_count = sum(1 for item in self.required_items if item.status == "SATISFIED")
        open_count = required_count - satisfied_count
        return {
            "report_id": self.report_id,
            "report_version": REPORT_VERSION,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "checklist_version": self.checklist_version,
            "decisions_version": self.decisions_version,
            "required_count": required_count,
            "satisfied_count": satisfied_count,
            "open_count": open_count,
            "required_items": [item.to_payload() for item in self.required_items],
            "blocked_actions": list(self.blocked_actions),
            "blocked_reasons": list(self.blocked_reasons),
        }


def load_real_data_readiness_checklist(path: Path) -> RealDataReadinessChecklist:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RealDataReadinessChecklist(
        version=data["version"],
        required_items=tuple(
            RealDataReadinessItem(
                item_id=item["item_id"],
                label=item["label"],
                status=item["status"],
                owner=item["owner"],
                required_before=item["required_before"],
            )
            for item in data["required_items"]
        ),
        blocked_actions=tuple(data["blocked_actions"]),
    )


def _require_decision_field(entry: dict[str, Any], field: str, index: int) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"decision {index} requires a non-empty '{field}' field")
    return value


def _find_exchange_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "agent-exchange").is_dir():
            return candidate
    return None


def _require_under_decisions(path: Path, project_root: Path, *, kind: str) -> Path:
    decisions_dir = (project_root / "agent-exchange/decisions").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(decisions_dir)
    except ValueError as error:
        raise ValueError(f"{kind} must live under agent-exchange/decisions") from error
    return resolved


def _resolve_evidence_path(project_root: Path, evidence_path: str) -> Path:
    candidate = Path(evidence_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
    _require_under_decisions(resolved, project_root, kind="evidence path")
    if resolved.suffix.lower() != ".md":
        raise ValueError("evidence path must point to a markdown decision record")
    if not resolved.exists():
        raise ValueError(f"evidence path does not exist: {evidence_path}")
    return resolved


def _markdown_field(text: str, name: str) -> str | None:
    lines = text.splitlines()
    label = f"{name}:"
    for index, line in enumerate(lines):
        if line.strip() == label:
            for candidate in lines[index + 1 :]:
                stripped = candidate.strip()
                if stripped:
                    return stripped
    return None


def _validate_human_decision_record(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required_fields = ("Approver", "Created at", "Scope", "Decision", "Evidence")
    missing = [field for field in required_fields if _markdown_field(text, field) is None]
    if missing:
        raise ValueError(
            f"human decision record {path} is missing required fields: "
            + ", ".join(missing)
        )


def _validate_approved_decision_source(
    source_path: Path,
    decision: RealDataDecision,
) -> None:
    project_root = _find_exchange_root(source_path.parent)
    if project_root is None:
        raise ValueError("approved decision files require an agent-exchange root")
    _require_under_decisions(source_path, project_root, kind="approved decision file")
    for evidence_path in decision.evidence:
        _validate_human_decision_record(_resolve_evidence_path(project_root, evidence_path))


def load_real_data_decisions(path: Path) -> RealDataDecisionFile:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("decision file must be a mapping")
    version = data.get("version")
    if version != DECISIONS_VERSION:
        raise ValueError(f"decision file version must be '{DECISIONS_VERSION}'")
    raw_decisions = data.get("decisions")
    if not isinstance(raw_decisions, list):
        raise ValueError("decision file requires a 'decisions' list")
    decisions = []
    for index, entry in enumerate(raw_decisions):
        if not isinstance(entry, dict):
            raise ValueError(f"decision {index} must be a mapping")
        decision_value = _require_decision_field(entry, "decision", index)
        if decision_value not in _DECISION_VALUES:
            raise ValueError(
                f"decision {index} has invalid decision value '{decision_value}'; "
                f"expected one of {list(_DECISION_VALUES)}"
            )
        decided_at = _require_decision_field(entry, "decided_at", index)
        try:
            parsed = datetime.fromisoformat(decided_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"decision {index} has invalid 'decided_at' timestamp") from error
        if parsed.tzinfo is None:
            raise ValueError(f"decision {index} 'decided_at' must carry an explicit UTC offset")
        evidence = entry.get("evidence")
        if (
            not isinstance(evidence, list)
            or not evidence
            or any(not isinstance(item, str) or not item.strip() for item in evidence)
        ):
            raise ValueError(f"decision {index} requires a non-empty 'evidence' list of strings")
        decision = RealDataDecision(
            item_id=_require_decision_field(entry, "item_id", index),
            decision=decision_value,
            approver=_require_decision_field(entry, "approver", index),
            decided_at=decided_at,
            scope=_require_decision_field(entry, "scope", index),
            evidence=tuple(evidence),
        )
        if decision.decision == APPROVED_DECISION:
            _validate_approved_decision_source(path, decision)
        decisions.append(decision)
    return RealDataDecisionFile(version=version, decisions=tuple(decisions))


def _reject_fixture_evidence(decision: RealDataDecision) -> None:
    for text in (decision.scope, *decision.evidence):
        normalized = text.replace("\\", "/").lower()
        for marker in _FORBIDDEN_EVIDENCE_MARKERS:
            if marker in normalized:
                raise ValueError(
                    f"{marker} data cannot satisfy real-data readiness item "
                    f"'{decision.item_id}'"
                )


def apply_real_data_decisions(
    checklist: RealDataReadinessChecklist,
    decision_file: RealDataDecisionFile,
) -> RealDataReadinessChecklist:
    known_ids = {item.item_id for item in checklist.required_items}
    decisions_by_item: dict[str, RealDataDecision] = {}
    for decision in decision_file.decisions:
        if decision.item_id not in known_ids:
            raise ValueError(f"unknown checklist item_id '{decision.item_id}'")
        if decision.item_id in decisions_by_item:
            raise ValueError(f"duplicate decision for item_id '{decision.item_id}'")
        if decision.decision == APPROVED_DECISION:
            _reject_fixture_evidence(decision)
        decisions_by_item[decision.item_id] = decision
    required_items = []
    for item in checklist.required_items:
        decision = decisions_by_item.get(item.item_id)
        if decision is None:
            required_items.append(item)
        elif decision.decision == APPROVED_DECISION:
            required_items.append(replace(item, status="SATISFIED", decision=decision))
        else:
            required_items.append(replace(item, decision=decision))
    return RealDataReadinessChecklist(
        version=checklist.version,
        required_items=tuple(required_items),
        blocked_actions=checklist.blocked_actions,
    )


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def build_real_data_readiness_report(
    checklist: RealDataReadinessChecklist,
    *,
    created_at: datetime,
    decisions: RealDataDecisionFile | None = None,
) -> RealDataReadinessReport:
    if decisions is not None:
        checklist = apply_real_data_decisions(checklist, decisions)
    decisions_version = decisions.version if decisions is not None else None
    open_items = [item for item in checklist.required_items if item.status != "SATISFIED"]
    if not open_items and "BUILD_PRODUCTION_TRAINING_DATASET" not in checklist.blocked_actions:
        status = "READY_FOR_PRODUCTION_DATASET"
    else:
        status = "BLOCKED"
    blocked_reasons = tuple(f"MISSING_{item.item_id}" for item in open_items)
    id_payload = {
        "created_at": utc_iso(created_at),
        "checklist_version": checklist.version,
        "decisions_version": decisions_version,
        "required_items": [item.to_payload() for item in checklist.required_items],
        "status": status,
    }
    return RealDataReadinessReport(
        report_id=_report_id(id_payload),
        created_at=created_at,
        status=status,
        checklist_version=checklist.version,
        decisions_version=decisions_version,
        required_items=checklist.required_items,
        blocked_actions=checklist.blocked_actions,
        blocked_reasons=blocked_reasons,
    )
