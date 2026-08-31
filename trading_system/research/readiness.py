from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.features.contracts import utc_iso

REPORT_VERSION = "real-data-readiness-report-0.1.0"


@dataclass(frozen=True)
class RealDataReadinessItem:
    item_id: str
    label: str
    status: str
    owner: str
    required_before: str

    def to_payload(self) -> dict[str, str]:
        return {
            "item_id": self.item_id,
            "label": self.label,
            "status": self.status,
            "owner": self.owner,
            "required_before": self.required_before,
        }


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


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def build_real_data_readiness_report(
    checklist: RealDataReadinessChecklist,
    *,
    created_at: datetime,
) -> RealDataReadinessReport:
    open_items = [item for item in checklist.required_items if item.status != "SATISFIED"]
    status = "READY_FOR_PRODUCTION_DATASET" if not open_items else "BLOCKED"
    blocked_reasons = tuple(f"MISSING_{item.item_id}" for item in open_items)
    id_payload = {
        "created_at": utc_iso(created_at),
        "checklist_version": checklist.version,
        "item_statuses": {item.item_id: item.status for item in checklist.required_items},
        "status": status,
    }
    return RealDataReadinessReport(
        report_id=_report_id(id_payload),
        created_at=created_at,
        status=status,
        checklist_version=checklist.version,
        required_items=checklist.required_items,
        blocked_actions=checklist.blocked_actions,
        blocked_reasons=blocked_reasons,
    )
