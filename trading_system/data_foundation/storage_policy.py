from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True)
class RawDataRetentionPolicy:
    version: str
    mode: str
    allowed_input_modes: tuple[str, ...]
    source_status_required: str
    raw_copy_allowed: bool
    raw_mutation_allowed: bool
    network_upload_allowed: bool
    manifest_output_allowed: bool
    dry_run_output_allowed: bool
    license_review_required: bool
    human_retention_approval_required: bool
    approved_storage_roots: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    required_manifest_fields: tuple[str, ...]
    owner: str


@dataclass(frozen=True)
class RawDataRetentionDecision:
    policy_version: str
    status: str
    source_id: str
    source_status: str
    raw_copy_allowed: bool
    raw_mutation_allowed: bool
    network_upload_allowed: bool
    manifest_output_allowed: bool
    dry_run_output_allowed: bool
    retention_approved: bool
    forbidden_actions: tuple[str, ...]
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "status": self.status,
            "source_id": self.source_id,
            "source_status": self.source_status,
            "raw_copy_allowed": self.raw_copy_allowed,
            "raw_mutation_allowed": self.raw_mutation_allowed,
            "network_upload_allowed": self.network_upload_allowed,
            "manifest_output_allowed": self.manifest_output_allowed,
            "dry_run_output_allowed": self.dry_run_output_allowed,
            "retention_approved": self.retention_approved,
            "forbidden_actions": list(self.forbidden_actions),
            "blocked_reasons": list(self.blocked_reasons),
        }


def load_raw_data_retention_policy(path: Path) -> RawDataRetentionPolicy:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RawDataRetentionPolicy(
        version=data["version"],
        mode=data["mode"],
        allowed_input_modes=tuple(data["allowed_input_modes"]),
        source_status_required=data["source_status_required"],
        raw_copy_allowed=bool(data["raw_copy_allowed"]),
        raw_mutation_allowed=bool(data["raw_mutation_allowed"]),
        network_upload_allowed=bool(data["network_upload_allowed"]),
        manifest_output_allowed=bool(data["manifest_output_allowed"]),
        dry_run_output_allowed=bool(data["dry_run_output_allowed"]),
        license_review_required=bool(data["license_review_required"]),
        human_retention_approval_required=bool(data["human_retention_approval_required"]),
        approved_storage_roots=tuple(data["approved_storage_roots"]),
        forbidden_actions=tuple(data["forbidden_actions"]),
        required_manifest_fields=tuple(data["required_manifest_fields"]),
        owner=data["owner"],
    )


def _missing_manifest_fields(policy: RawDataRetentionPolicy, manifest: Mapping[str, Any]) -> list[str]:
    return sorted(field for field in policy.required_manifest_fields if field not in manifest)


def evaluate_raw_data_retention(
    policy: RawDataRetentionPolicy,
    manifest: Mapping[str, Any],
) -> RawDataRetentionDecision:
    reasons: list[str] = []
    missing = _missing_manifest_fields(policy, manifest)
    if missing:
        reasons.append("MISSING_REQUIRED_MANIFEST_FIELDS")
    if manifest.get("source_status") != policy.source_status_required:
        reasons.append("SOURCE_STATUS_NOT_OPEN_HUMAN_DECISION")
    if policy.human_retention_approval_required:
        reasons.append("RAW_RETENTION_REQUIRES_HUMAN_APPROVAL")
    if policy.license_review_required:
        reasons.append("LICENSE_REVIEW_REQUIRED")
    if policy.approved_storage_roots:
        reasons.append("APPROVED_STORAGE_ROOTS_MUST_BE_EMPTY_UNTIL_APPROVAL")

    manifest_only_allowed = (
        not missing
        and manifest.get("source_status") == policy.source_status_required
        and policy.manifest_output_allowed
        and policy.dry_run_output_allowed
        and not policy.raw_copy_allowed
        and not policy.raw_mutation_allowed
        and not policy.network_upload_allowed
    )
    return RawDataRetentionDecision(
        policy_version=policy.version,
        status="MANIFEST_ONLY_ALLOWED" if manifest_only_allowed else "BLOCKED",
        source_id=str(manifest.get("source_id", "UNKNOWN_SOURCE")),
        source_status=str(manifest.get("source_status", "UNKNOWN_STATUS")),
        raw_copy_allowed=False,
        raw_mutation_allowed=False,
        network_upload_allowed=False,
        manifest_output_allowed=policy.manifest_output_allowed,
        dry_run_output_allowed=policy.dry_run_output_allowed,
        retention_approved=False,
        forbidden_actions=policy.forbidden_actions,
        blocked_reasons=tuple(reasons),
    )
