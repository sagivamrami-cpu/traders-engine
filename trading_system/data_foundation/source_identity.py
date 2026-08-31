from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True)
class FixtureModePolicy:
    source_ids: tuple[str, ...]
    canonical_symbols: tuple[str, ...]
    graph_ids: tuple[str, ...]
    dataset_ids: tuple[str, ...]


@dataclass(frozen=True)
class RealSourcePolicy:
    required_metadata_fields: tuple[str, ...]
    allowed_source_statuses: tuple[str, ...]
    forbidden_identifier_prefixes: tuple[str, ...]
    forbidden_identifier_fragments: tuple[str, ...]


@dataclass(frozen=True)
class SourceIdentityPolicy:
    version: str
    fixture_mode: FixtureModePolicy
    real_source: RealSourcePolicy
    allowed_deferred_producers: tuple[str, ...]
    blocked_actions: tuple[str, ...]


@dataclass(frozen=True)
class SourceIdentityValidation:
    status: str
    source_id: str
    canonical_symbol: str
    mode: str
    production_allowed: bool
    blocked_actions: tuple[str, ...]
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_id": self.source_id,
            "canonical_symbol": self.canonical_symbol,
            "mode": self.mode,
            "production_allowed": self.production_allowed,
            "blocked_actions": list(self.blocked_actions),
            "blocked_reasons": list(self.blocked_reasons),
        }


def _strings(values: list[Any]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


def load_source_identity_policy(path: Path) -> SourceIdentityPolicy:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fixture = data["fixture_mode"]
    real_source = data["real_source"]
    return SourceIdentityPolicy(
        version=str(data["version"]),
        fixture_mode=FixtureModePolicy(
            source_ids=_strings(fixture["source_ids"]),
            canonical_symbols=_strings(fixture["canonical_symbols"]),
            graph_ids=_strings(fixture["graph_ids"]),
            dataset_ids=_strings(fixture["dataset_ids"]),
        ),
        real_source=RealSourcePolicy(
            required_metadata_fields=_strings(real_source["required_metadata_fields"]),
            allowed_source_statuses=_strings(real_source["allowed_source_statuses"]),
            forbidden_identifier_prefixes=_strings(real_source["forbidden_identifier_prefixes"]),
            forbidden_identifier_fragments=_strings(real_source["forbidden_identifier_fragments"]),
        ),
        allowed_deferred_producers=_strings(data["allowed_deferred_producers"]),
        blocked_actions=_strings(data["blocked_actions"]),
    )


def _string_metadata(metadata: Mapping[str, Any], field: str) -> str:
    value = metadata.get(field, "")
    return value.strip() if isinstance(value, str) else str(value).strip()


def _is_decision_ref(value: str) -> bool:
    if not value:
        return False
    normalized = value.replace("\\", "/")
    return normalized.startswith("agent-exchange/decisions/") and normalized.endswith(".md")


def _has_forbidden_identifier(value: str, policy: SourceIdentityPolicy) -> bool:
    lowered = value.lower()
    return any(
        lowered.startswith(prefix.lower()) for prefix in policy.real_source.forbidden_identifier_prefixes
    ) or any(fragment.lower() in lowered for fragment in policy.real_source.forbidden_identifier_fragments)


def validate_source_identity(
    metadata: Mapping[str, Any],
    policy: SourceIdentityPolicy,
) -> SourceIdentityValidation:
    source_id = _string_metadata(metadata, "source_id")
    canonical_symbol = _string_metadata(metadata, "canonical_symbol")
    reasons: list[str] = []

    fixture_source = source_id in policy.fixture_mode.source_ids
    fixture_symbol = canonical_symbol in policy.fixture_mode.canonical_symbols
    if fixture_source and fixture_symbol:
        return SourceIdentityValidation(
            status="FIXTURE_ONLY",
            source_id=source_id,
            canonical_symbol=canonical_symbol,
            mode="FIXTURE",
            production_allowed=False,
            blocked_actions=policy.blocked_actions,
            blocked_reasons=("FIXTURE_ONLY_NOT_FOR_PRODUCTION",),
        )
    if fixture_source and not fixture_symbol:
        reasons.append("FIXTURE_SOURCE_ID_REQUIRES_FIXTURE_SYMBOL")
    if fixture_symbol and not fixture_source:
        reasons.append("FIXTURE_SYMBOL_FORBIDDEN_FOR_REAL_SOURCE")

    for field in policy.real_source.required_metadata_fields:
        if not _string_metadata(metadata, field):
            reasons.append(f"MISSING_{field.upper()}")

    source_status = _string_metadata(metadata, "source_status")
    if source_status and source_status not in policy.real_source.allowed_source_statuses:
        reasons.append("SOURCE_STATUS_NOT_ALLOWED_FOR_REAL_SOURCE")

    decision_ref = _string_metadata(metadata, "human_decision_ref")
    if not decision_ref:
        if "MISSING_HUMAN_DECISION_REF" not in reasons:
            reasons.append("MISSING_HUMAN_DECISION_REF")
    elif not _is_decision_ref(decision_ref):
        reasons.append("HUMAN_DECISION_REF_OUTSIDE_DECISIONS")

    for field in ("source_id", "canonical_symbol", "graph_id", "dataset_id"):
        value = _string_metadata(metadata, field)
        if value and _has_forbidden_identifier(value, policy):
            reasons.append("FIXTURE_IDENTIFIER_FRAGMENT_FORBIDDEN")
            break

    if reasons:
        return SourceIdentityValidation(
            status="BLOCKED",
            source_id=source_id,
            canonical_symbol=canonical_symbol,
            mode="REAL_SOURCE",
            production_allowed=False,
            blocked_actions=policy.blocked_actions,
            blocked_reasons=tuple(dict.fromkeys(reasons)),
        )

    return SourceIdentityValidation(
        status="REAL_SOURCE_PENDING_HUMAN_DECISION",
        source_id=source_id,
        canonical_symbol=canonical_symbol,
        mode="REAL_SOURCE",
        production_allowed=False,
        blocked_actions=policy.blocked_actions,
        blocked_reasons=("PRODUCTION_APPROVAL_REQUIRED",),
    )
