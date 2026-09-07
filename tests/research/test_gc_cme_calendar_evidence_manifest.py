import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import ValidationError
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "configs/data/gc-session-calendar-cme-evidence-manifest.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_cme_calendar_evidence_manifest.schema.json"
CREATED_AT = datetime(2026, 9, 2, 1, 30, tzinfo=UTC)


def validate_manifest_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_gc_cme_calendar_evidence_manifest_is_official_but_fail_closed():
    from trading_system.research.gc_cme_calendar_evidence_manifest import (
        build_gc_cme_calendar_evidence_manifest_report,
    )

    payload = build_gc_cme_calendar_evidence_manifest_report(
        MANIFEST_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_manifest_payload(payload)
    assert payload["status"] == "OFFICIAL_CME_REFERENCES_RECORDED_HISTORICAL_EVIDENCE_INCOMPLETE"
    assert payload["session_calendar_gate_status"] == "UNSATISFIED_CME_EVIDENCE_MANIFEST_ONLY"
    assert payload["authoritative_source_family"] == "CME_GROUP_PUBLIC_REFERENCES"
    assert len(payload["sources"]) == 2
    assert all(source["source_type"] == "CME_GROUP_OFFICIAL_PUBLIC_WEB" for source in payload["sources"])
    assert all(source["retrieved_at"] is None for source in payload["sources"])
    assert all(source["content_sha256"] is None for source in payload["sources"])
    assert payload["sources"][0]["url"] == "https://www.cmegroup.com/markets/metals/precious/gold.contractSpecs.html"
    assert payload["sources"][1]["url"] == "https://www.cmegroup.com/trading-hours.html"
    assert payload["coverage_assessment"]["current_product_reference_available"] is True
    assert payload["coverage_assessment"]["historical_era_coverage_complete"] is False
    assert payload["coverage_assessment"]["calendar_overlay_complete"] is False
    assert "FINE_GRAINED_OBSERVED_GAP_PROFILE" in payload["required_missing_evidence"]
    assert payload["calendar_registration_allowed"] is False
    assert payload["dataset_construction_allowed"] is False
    assert payload["resampling_allowed"] is False
    assert payload["training_allowed"] is False
    assert "REGISTER_SESSION_CALENDAR" in payload["blocked_actions"]


def test_gc_cme_calendar_evidence_manifest_rejects_non_cme_urls():
    from trading_system.research.gc_cme_calendar_evidence_manifest import (
        build_gc_cme_calendar_evidence_manifest_report,
    )

    payload = build_gc_cme_calendar_evidence_manifest_report(
        MANIFEST_PATH,
        created_at=CREATED_AT,
    ).to_payload()
    payload["sources"][0]["url"] = "https://example.com/not-cme"

    with pytest.raises(ValidationError):
        validate_manifest_payload(payload)


def test_gc_cme_calendar_evidence_manifest_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_cme_calendar_evidence_manifest.py",
            "--manifest",
            "configs/data/gc-session-calendar-cme-evidence-manifest.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_manifest_payload(payload)
    assert payload["status"] == "OFFICIAL_CME_REFERENCES_RECORDED_HISTORICAL_EVIDENCE_INCOMPLETE"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""
