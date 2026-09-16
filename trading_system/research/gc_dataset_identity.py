"""Deterministic identity for the first real GC 30m research dataset.

``dataset_id`` is the sha256 of a stable JSON document made of: input archive
sha256s, sha256s of the rule-bearing configs and schemas (newline-normalised),
and the builder's rule constants. Status documents (the dataset contract,
label/split and timestamp policies) are deliberately excluded so that the
construction-authorization record can bind to ``dataset_id`` without a
circular dependency; their rule values are mirrored in the builder constants
and asserted equal by tests.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.manifests import to_plain_data, validate_json_payload
from trading_system.features.contracts import utc_iso
from trading_system.research import gc_real_dataset_builder as builder

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_VERSION = "gc-dataset-identity-manifest-0.1.0"
MODE = "GC_DATASET_IDENTITY"
SCHEMA_PATH = ROOT / "schemas/gc_dataset_identity_manifest.schema.json"
ARCHIVE_KEYS = ("ohlcv_1s", "order_flow_1m")


@dataclass(frozen=True)
class GcDatasetIdentityManifest:
    payload: dict[str, Any]

    @property
    def dataset_id(self) -> str:
        return str(self.payload["dataset_id"])

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_text_file(path: Path) -> str:
    """sha256 of a text file with CRLF normalised to LF (Windows checkouts)."""
    return _sha256_hex(path.read_text(encoding="utf-8").replace("\r\n", "\n"))


def load_identity_config(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected GC dataset identity config mapping")
    return to_plain_data(loaded)


def _canonical_manifest_sha256(ref: str, root: Path) -> str:
    manifest = yaml.safe_load((root / ref).read_text(encoding="utf-8"))
    return str(manifest["archive_sha256"])


def compute_local_archive_hashes(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    """sha256 + size for local archive files, keyed by archive key. Paths never leave this call."""
    result: dict[str, dict[str, Any]] = {}
    for key, path in paths.items():
        result[key] = {"sha256": sha256_file(path), "size_bytes": int(path.stat().st_size)}
    return result


def build_gc_dataset_identity(
    config_path: Path,
    *,
    created_at: datetime,
    local_archive_hashes: dict[str, dict[str, Any]] | None = None,
    root: Path | None = None,
) -> GcDatasetIdentityManifest:
    root = root or ROOT
    config = load_identity_config(config_path)
    blocked_reasons: list[str] = []
    archives: dict[str, dict[str, Any]] = {}
    for key in ARCHIVE_KEYS:
        spec = config["input_archives"][key]
        expected = str(spec["expected_sha256"])
        canonical = _canonical_manifest_sha256(str(spec["canonical_manifest_ref"]), root)
        if canonical != expected:
            blocked_reasons.append(f"{key.upper()}_EXPECTED_SHA256_DIFFERS_FROM_CANONICAL_MANIFEST")
        verified = False
        if local_archive_hashes is not None:
            local = local_archive_hashes.get(key)
            if local is None:
                blocked_reasons.append(f"{key.upper()}_LOCAL_ARCHIVE_HASH_MISSING")
            else:
                if str(local["sha256"]) != expected:
                    blocked_reasons.append(f"{key.upper()}_LOCAL_ARCHIVE_SHA256_MISMATCH")
                if int(local["size_bytes"]) != int(spec["expected_size_bytes"]):
                    blocked_reasons.append(f"{key.upper()}_LOCAL_ARCHIVE_SIZE_MISMATCH")
                verified = str(local["sha256"]) == expected and int(local["size_bytes"]) == int(spec["expected_size_bytes"])
        entry: dict[str, Any] = {
            "source_type": str(spec["source_type"]),
            "canonical_manifest_ref": str(spec["canonical_manifest_ref"]),
            "sha256": expected,
            "size_bytes": int(spec["expected_size_bytes"]),
            "verified_against_local_file": verified,
        }
        if "member_pattern" in spec:
            entry["member_pattern"] = str(spec["member_pattern"])
        if "selected_member" in spec:
            entry["selected_member"] = str(spec["selected_member"])
        archives[key] = entry

    config_hashes = {ref: hash_text_file(root / ref) for ref in config["governing_configs"]}
    schema_hashes = {ref: hash_text_file(root / ref) for ref in config["governing_schemas"]}
    rules = builder.rule_constants()
    identity_document = {
        "dataset_name": str(config["dataset_name"]),
        "builder_module": str(config["builder_module"]),
        "input_archives": {key: archives[key]["sha256"] for key in ARCHIVE_KEYS},
        "config_hashes": config_hashes,
        "schema_hashes": schema_hashes,
        "rules": rules,
    }
    dataset_id = _sha256_hex(stable_json_dumps(identity_document))
    if config.get("dataset_construction_allowed") is not False:
        blocked_reasons.append("DATASET_CONSTRUCTION_MUST_REMAIN_BLOCKED_IN_IDENTITY_CONFIG")
    if config.get("training_allowed") is not False:
        blocked_reasons.append("TRAINING_MUST_REMAIN_BLOCKED_IN_IDENTITY_CONFIG")
    all_verified = all(archives[key]["verified_against_local_file"] for key in ARCHIVE_KEYS)
    body = {
        "manifest_version": MANIFEST_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "dataset_name": str(config["dataset_name"]),
        "dataset_id": dataset_id,
        "canonical_symbol": str(config["canonical_symbol"]),
        "candidate_timeframe": str(config["candidate_timeframe"]),
        "contract_ref": str(config["contract_ref"]),
        "contract_hashing_policy": str(config["contract_hashing_policy"]),
        "builder_module": str(config["builder_module"]),
        "builder_version": builder.BUILDER_VERSION,
        "identity_source": "LOCAL_ARCHIVE_VERIFIED" if all_verified else "CANONICAL_MANIFEST_DECLARED",
        "input_archives": archives,
        "config_hashes": config_hashes,
        "schema_hashes": schema_hashes,
        "rules": rules,
        "required_components": list(config["required_components"]),
        "contract_identity_status": str(config["contract_identity_status"]),
        "dataset_identity_gate_status": "SATISFIED_DETERMINISTIC_IDENTITY_V1" if not blocked_reasons else "UNSATISFIED",
        "dataset_construction_allowed": False,
        "training_allowed": False,
        "blocked_reasons": blocked_reasons,
    }
    manifest_id = _sha256_hex(stable_json_dumps(body))
    return GcDatasetIdentityManifest(payload={"manifest_id": manifest_id, **body})


def load_identity_manifest(path: Path) -> dict[str, Any]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_json_payload(SCHEMA_PATH, payload)
    return payload
