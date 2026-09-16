# Phase 19 Local-Only Real Source Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-only, sanitized real-source bundle packet that can prepare manifest metadata after a successful Phase 18 preflight without authorizing dry-run, dataset construction, model training, promotion, live trading, broker execution, or capital allocation.

**Architecture:** Create a new `trading_system/research/real_source_bundle.py` module instead of opening the existing fixture-only `csv_onboarding.py` and `source_bundle.py` paths to real sources. The new module consumes Phase 18 preflight output, validates CSV shape and symbol normalization with a project-root-aware symbol map, emits a redacted manifest-like payload, evaluates retention in manifest-only mode, and always leaves production gates blocked. This phase is the first controlled real-source preparation step, not a training or backtest step.

**Tech Stack:** Python 3, pytest, jsonschema Draft 2020-12, PyYAML, existing `trading_system.data_foundation` and `trading_system.research` helpers.

**Spec:** `docs/implementation-reports/phase-18-real-source-onboarding-preflight.md`

## Global Constraints

- Codex remains architecture authority and final acceptance owner.
- Claude Code may implement scoped tasks assigned by Codex.
- Groq reviews for contradiction, hidden approval, leakage, and unsafe paths.
- Human decision records under `agent-exchange/decisions/` are required before real data can move beyond report-only preflight.
- Phase 19 may prepare only sanitized local manifest metadata.
- Phase 19 must not run offline dry-run, build datasets, train models, promote models, execute broker actions, allocate capital, or deploy.
- No raw CSV rows, secrets, credentials, account identifiers, absolute local paths, or private source details may be written to `agent-exchange/`.
- `REAL_SOURCE_PENDING_HUMAN_DECISION` must remain blocked from fixture onboarding, fixture source bundle validation, and dry-run.
- `PREFLIGHT_RECORDS_PRESENT_PRODUCTION_BLOCKED` is a precondition for local-only real-source bundle preparation, not production approval.

---

### Task 1: Add Failing Real-Source Local Bundle Tests

**Files:**
- Create: `tests/research/test_real_source_local_bundle.py`

**Interfaces:**
- Consumes: `build_real_source_onboarding_preflight(csv_path, metadata_path, decisions_path, created_at, project_root=None)`.
- Produces test expectations for `build_real_source_local_bundle(csv_path, metadata_path, decisions_path, retention_policy_path, created_at, project_root=None)`.

- [ ] **Step 1: Write shared test helpers**

Create a temporary project root with copied policies and a temporary `SPY.US` symbol map. Use an edited copy of `tests/fixtures/data_foundation/raw/ohlcv_fixture.csv` where the invalid high/low row is corrected.

```python
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.research.real_source_local_bundle import build_real_source_local_bundle

ROOT = Path(__file__).resolve().parents[2]
CREATED_AT = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


def valid_csv(path: Path) -> Path:
    path.write_text(
        FIXTURE_CSV.read_text(encoding="utf-8").replace(
            "SPY,2026-08-28T09:35:00,451.50,450.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
            "SPY,2026-08-28T09:35:00,451.50,451.80,451.00,451.10,800,ORIGINAL,2026-08-28T09:35:05",
        ),
        encoding="utf-8",
    )
    return path


def write_record(path: Path, *, decision: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "Approver: Human Data Owner",
                "Created at: 2026-08-31T21:00:00Z",
                "Scope: Phase 19 local-only real-source bundle test",
                f"Decision: {decision}",
                "Evidence: Temporary test record; not production approval",
            ]
        ),
        encoding="utf-8",
    )


def write_real_source_project(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    project_root = tmp_path / "project"
    (project_root / "configs/data").mkdir(parents=True)
    (project_root / "configs/research").mkdir(parents=True)
    shutil.copyfile(ROOT / "configs/data/normalization-policy.yaml", project_root / "configs/data/normalization-policy.yaml")
    shutil.copyfile(ROOT / "configs/data/source-identity-policy.yaml", project_root / "configs/data/source-identity-policy.yaml")
    shutil.copyfile(ROOT / "configs/data/raw-data-retention-policy.yaml", project_root / "configs/data/raw-data-retention-policy.yaml")
    shutil.copyfile(ROOT / "configs/research/real-data-readiness-checklist.yaml", project_root / "configs/research/real-data-readiness-checklist.yaml")
    (project_root / "configs/data/symbol-map.yaml").write_text(
        "\n".join(
            [
                "version: symbol-map-0.1.0",
                "symbols:",
                "  - canonical_symbol: SPY.US",
                "    asset_class: EQUITY_ETF",
                "    venue: TEST_REAL_SOURCE",
                "    raw_symbols: [SPY]",
                "    contract_policy: not_applicable",
            ]
        ),
        encoding="utf-8",
    )
    write_record(project_root / "agent-exchange/decisions/source.md", decision="APPROVED")
    write_record(project_root / "agent-exchange/decisions/approved.md", decision="APPROVED")
    write_record(project_root / "agent-exchange/decisions/deferred.md", decision="DEFERRED")
    metadata = yaml.safe_load((ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml").read_text(encoding="utf-8"))
    metadata.update(
        {
            "source_id": "real-ohlcv-spy-1m",
            "asset_class": "EQUITY_ETF",
            "venue": "TEST_REAL_SOURCE",
            "canonical_symbol": "SPY.US",
            "raw_symbol": "SPY",
            "timeframe": "1m",
            "timezone": "America/New_York",
            "session_calendar_id": "us-equities-regular-v1",
            "human_decision_ref": "agent-exchange/decisions/source.md",
        }
    )
    metadata_path = project_root / "configs/data/real-source.yaml"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=True), encoding="utf-8")
    decisions_path = project_root / "agent-exchange/decisions/decisions.yaml"
    decisions_path.write_text(
        yaml.safe_dump(
            {
                "version": "real-data-decisions-0.1.0",
                "decisions": [
                    {
                        "item_id": item_id,
                        "decision": decision,
                        "approver": "Human Data Owner",
                        "decided_at": "2026-08-31T21:00:00Z",
                        "scope": "Phase 19 local-only bundle test",
                        "evidence": [f"agent-exchange/decisions/{decision.lower()}.md"],
                    }
                    for item_id, decision in {
                        "REAL_HISTORICAL_OHLCV_CSV": "APPROVED",
                        "PRODUCTION_OHLCV_VENDOR_DECISION": "APPROVED",
                        "FIRST_REAL_SYMBOL": "APPROVED",
                        "FIRST_HISTORICAL_INTERVAL": "APPROVED",
                        "RAW_DATA_STORAGE_LICENSE_APPROVAL": "APPROVED",
                        "ORDER_FLOW_SOURCE_DECISION": "DEFERRED",
                        "OPTIONS_SOURCE_DECISION": "DEFERRED",
                    }.items()
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return (
        project_root,
        metadata_path,
        decisions_path,
        project_root / "configs/data/raw-data-retention-policy.yaml",
    )


def validate_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/real_source_local_bundle.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
```

- [ ] **Step 2: Write blocked-default test**

```python
def test_real_source_local_bundle_blocks_without_accepted_preflight(tmp_path: Path):
    payload = build_real_source_local_bundle(
        valid_csv(tmp_path / "valid.csv"),
        ROOT / "configs/data/real-ohlcv-source-metadata-template.yaml",
        None,
        ROOT / "configs/data/raw-data-retention-policy.yaml",
        created_at=CREATED_AT,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert payload["production_allowed"] is False
    assert payload["local_manifest"] is None
    assert payload["dry_run_summary"] is None
    assert payload["allowed_next_actions"] == []
    assert "PREFLIGHT_NOT_RECORDS_PRESENT" in payload["blocked_reasons"]
```

- [ ] **Step 3: Write records-present local manifest test**

```python
def test_real_source_local_bundle_prepares_redacted_manifest_only(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path, retention_path = write_real_source_project(tmp_path)

    payload = build_real_source_local_bundle(
        csv_path,
        metadata_path,
        decisions_path,
        retention_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()

    validate_payload(payload)
    assert payload["status"] == "LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED"
    assert payload["production_allowed"] is False
    assert payload["allowed_next_actions"] == []
    assert payload["dry_run_summary"] is None
    assert payload["local_manifest"]["raw_file"] == "LOCAL_PATH_REDACTED"
    assert payload["local_manifest"]["source_status"] == "OPEN_HUMAN_DECISION"
    assert payload["local_manifest"]["canonical_symbol"] == "SPY.US"
    assert payload["local_manifest"]["row_count"] > 0
    assert payload["retention_decision"]["retention_approved"] is False
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in payload["blocked_actions"]
```

- [ ] **Step 4: Write redaction regression test**

```python
def test_real_source_local_bundle_output_never_leaks_paths(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")
    project_root, metadata_path, decisions_path, retention_path = write_real_source_project(tmp_path)

    payload = build_real_source_local_bundle(
        csv_path,
        metadata_path,
        decisions_path,
        retention_path,
        created_at=CREATED_AT,
        project_root=project_root,
    ).to_payload()
    serialized = json.dumps(payload, sort_keys=True)

    assert str(csv_path) not in serialized
    assert str(metadata_path) not in serialized
    assert str(decisions_path) not in serialized
    assert str(retention_path) not in serialized
    assert "C:\\" not in serialized
    assert "/Users/" not in serialized
```

- [ ] **Step 5: Run tests to verify RED**

Run: `python -m pytest tests/research/test_real_source_local_bundle.py -v`

Expected: FAIL because `trading_system.research.real_source_local_bundle` and the schema do not exist.

---

### Task 2: Add Real-Source Local Bundle Schema

**Files:**
- Create: `schemas/real_source_local_bundle.schema.json`

**Interfaces:**
- Consumes: payload from `RealSourceLocalBundle.to_payload()`.
- Produces: JSON Schema validating the local-only contract.

- [ ] **Step 1: Create schema**

The schema must require:
- `bundle_id`
- `bundle_version`
- `mode`
- `created_at`
- `status`
- `csv_path`
- `metadata_path`
- `decisions_path`
- `retention_policy_path`
- `preflight`
- `source_identity`
- `local_manifest`
- `retention_decision`
- `dry_run_summary`
- `production_allowed`
- `allowed_next_actions`
- `blocked_actions`
- `blocked_reasons`

Rules:
- `bundle_version` const is `real-source-local-bundle-0.1.0`.
- `mode` const is `REAL_SOURCE_LOCAL_BUNDLE_PREPARATION`.
- Path fields must be `LOCAL_PATH_REDACTED` or `null` for missing decisions.
- `status` enum is `BLOCKED` or `LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED`.
- `production_allowed` const is `false`.
- `allowed_next_actions` must have `maxItems: 0`.
- `dry_run_summary` must be `null`.
- `source_identity.status` may be `REAL_SOURCE_PENDING_HUMAN_DECISION` or `BLOCKED`, never `FIXTURE_ONLY` for accepted output.
- `local_manifest` is `null` when `status == "BLOCKED"`.
- When `status == "LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED"`, `local_manifest` must include `source_id`, `source_status`, `canonical_symbol`, `raw_symbol`, `raw_file`, `raw_file_sha256`, `row_count`, `first_observed_at`, `last_observed_at`, and `ingested_at`.
- `local_manifest.raw_file` const is `LOCAL_PATH_REDACTED`.
- `blocked_actions` must include dataset construction, training, model promotion, live trading, broker execution, and capital allocation.

- [ ] **Step 2: Run schema tests**

Run: `python -m pytest tests/research/test_real_source_local_bundle.py::test_real_source_local_bundle_blocks_without_accepted_preflight -v`

Expected: FAIL until the production module exists.

---

### Task 3: Implement Local-Only Real-Source Bundle Module

**Files:**
- Create: `trading_system/research/real_source_local_bundle.py`

**Interfaces:**
- Consumes:
  - `build_real_source_onboarding_preflight(...)`
  - `read_csv_rows`, `normalize_ohlcv_row`, `load_normalization_policy`, `load_symbol_map`
  - `load_raw_data_retention_policy`, `evaluate_raw_data_retention`
  - `sha256_file`
- Produces:
  - `build_real_source_local_bundle(csv_path: Path, metadata_path: Path, decisions_path: Path | None, retention_policy_path: Path, *, created_at: datetime, project_root: Path | None = None) -> RealSourceLocalBundle`
  - `RealSourceLocalBundle.to_payload() -> dict[str, Any]`

- [ ] **Step 1: Implement dataclass and constants**

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.csv_onboarding import REQUIRED_OHLCV_COLUMNS, CsvOnboardingError
from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map, normalize_ohlcv_row, read_csv_rows
from trading_system.data_foundation.storage_policy import evaluate_raw_data_retention, load_raw_data_retention_policy
from trading_system.features.contracts import utc_iso
from trading_system.research.intake_packet import REDACTED_LOCAL_PATH
from trading_system.research.real_source_onboarding import RECORDS_PRESENT_STATUS, build_real_source_onboarding_preflight

BUNDLE_VERSION = "real-source-local-bundle-0.1.0"
MODE = "REAL_SOURCE_LOCAL_BUNDLE_PREPARATION"
PREPARED_STATUS = "LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED"
BLOCKED_ACTIONS = (
    "BUILD_PRODUCTION_TRAINING_DATASET",
    "TRAIN_PRODUCTION_MODEL",
    "CLAIM_EDGE",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
ROOT = Path(__file__).resolve().parents[2]
```

- [ ] **Step 2: Implement payload object**

```python
@dataclass(frozen=True)
class RealSourceLocalBundle:
    bundle_id: str
    created_at: datetime
    status: str
    decisions_path_present: bool
    preflight: dict[str, Any]
    source_identity: dict[str, Any]
    local_manifest: dict[str, Any] | None
    retention_decision: dict[str, Any]
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "bundle_version": BUNDLE_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "csv_path": REDACTED_LOCAL_PATH,
            "metadata_path": REDACTED_LOCAL_PATH,
            "decisions_path": REDACTED_LOCAL_PATH if self.decisions_path_present else None,
            "retention_policy_path": REDACTED_LOCAL_PATH,
            "preflight": self.preflight,
            "source_identity": self.source_identity,
            "local_manifest": self.local_manifest,
            "retention_decision": self.retention_decision,
            "dry_run_summary": None,
            "production_allowed": False,
            "allowed_next_actions": [],
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(self.blocked_reasons),
        }
```

- [ ] **Step 3: Implement sanitized manifest helper**

```python
def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise CsvOnboardingError("datetime must be timezone-aware")
    return value.isoformat().replace("+00:00", "Z")


def _validate_columns(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise CsvOnboardingError("csv contains no rows")
    missing = sorted(REQUIRED_OHLCV_COLUMNS - set(rows[0]))
    if missing:
        raise CsvOnboardingError(f"missing required columns: {', '.join(missing)}")


def _build_sanitized_manifest(csv_path: Path, metadata: dict[str, Any], *, created_at: datetime, root: Path) -> dict[str, Any]:
    normalization_policy = load_normalization_policy(root / "configs/data/normalization-policy.yaml")
    symbol_map = load_symbol_map(root / "configs/data/symbol-map.yaml")
    rows = read_csv_rows(csv_path)
    _validate_columns(rows)
    records = [
        normalize_ohlcv_row(
            row,
            normalization_policy,
            symbol_map,
            source_id=str(metadata["source_id"]),
            source_version=str(metadata["schema_version"]),
        )
        for row in rows
    ]
    observed_symbols = {record.canonical_symbol for record in records}
    canonical_symbol = str(metadata["canonical_symbol"])
    if observed_symbols != {canonical_symbol}:
        raise CsvOnboardingError("csv canonical symbols do not match metadata canonical_symbol: " + ", ".join(sorted(observed_symbols)))
    observed_at_values = [record.observed_at for record in records]
    return {
        "manifest_version": metadata["manifest_version"],
        "source_id": metadata["source_id"],
        "source_type": metadata["source_type"],
        "source_status": metadata["source_status"],
        "asset_class": metadata["asset_class"],
        "venue": metadata["venue"],
        "canonical_symbol": metadata["canonical_symbol"],
        "raw_symbol": metadata["raw_symbol"],
        "timeframe": metadata["timeframe"],
        "timezone": metadata["timezone"],
        "session_calendar_id": metadata["session_calendar_id"],
        "schema_version": metadata["schema_version"],
        "raw_file": REDACTED_LOCAL_PATH,
        "raw_file_sha256": sha256_file(csv_path),
        "row_count": len(rows),
        "first_observed_at": _format_utc(min(observed_at_values)),
        "last_observed_at": _format_utc(max(observed_at_values)),
        "ingested_at": _format_utc(created_at),
        "correction_policy": metadata["correction_policy"],
        "owner": "HUMAN_DATA_OWNER_REDACTED",
    }
```

- [ ] **Step 4: Implement build function**

```python
def _bundle_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _blocked_retention(retention_policy_path: Path) -> dict[str, Any]:
    return evaluate_raw_data_retention(load_raw_data_retention_policy(retention_policy_path), {}).to_payload()


def build_real_source_local_bundle(
    csv_path: Path,
    metadata_path: Path,
    decisions_path: Path | None,
    retention_policy_path: Path,
    *,
    created_at: datetime,
    project_root: Path | None = None,
) -> RealSourceLocalBundle:
    root = ROOT if project_root is None else project_root
    preflight = build_real_source_onboarding_preflight(
        csv_path,
        metadata_path,
        decisions_path,
        created_at=created_at,
        project_root=root,
    ).to_payload()
    source_identity = preflight["source_identity"]
    reasons: list[str] = []
    local_manifest: dict[str, Any] | None = None
    retention_decision = _blocked_retention(retention_policy_path)
    status = "BLOCKED"
    if preflight["status"] != RECORDS_PRESENT_STATUS:
        reasons.append("PREFLIGHT_NOT_RECORDS_PRESENT")
        reasons.extend(preflight["blocked_reasons"])
    else:
        try:
            metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
            local_manifest = _build_sanitized_manifest(csv_path, metadata, created_at=created_at, root=root)
            retention_decision = evaluate_raw_data_retention(load_raw_data_retention_policy(retention_policy_path), local_manifest).to_payload()
            status = PREPARED_STATUS
            reasons.extend(retention_decision["blocked_reasons"])
        except Exception:
            reasons.append("LOCAL_MANIFEST_PREPARATION_FAILED")
            local_manifest = None
    id_payload = {
        "created_at": utc_iso(created_at),
        "status": status,
        "preflight_id": preflight["preflight_id"],
        "source_identity": source_identity,
        "local_manifest": local_manifest,
        "retention_status": retention_decision["status"],
        "blocked_reasons": list(dict.fromkeys(reasons)),
    }
    return RealSourceLocalBundle(
        bundle_id=_bundle_id(id_payload),
        created_at=created_at,
        status=status,
        decisions_path_present=decisions_path is not None,
        preflight=preflight,
        source_identity=source_identity,
        local_manifest=local_manifest,
        retention_decision=retention_decision,
        blocked_reasons=tuple(dict.fromkeys(reasons)),
    )
```

- [ ] **Step 5: Run module tests**

Run: `python -m pytest tests/research/test_real_source_local_bundle.py -v`

Expected: PASS.

---

### Task 4: Add CLI and Validator

**Files:**
- Create: `tools/prepare_real_source_local_bundle.py`
- Create: `tools/validate_phase19.py`
- Create: `tests/research/test_phase19_validator.py`

**Interfaces:**
- Consumes: `build_real_source_local_bundle(...)`.
- Produces:
  - CLI command `python tools/prepare_real_source_local_bundle.py --csv <path> --metadata <path> --decisions <path> --retention-policy <path>`
  - validator `python tools/validate_phase19.py`

- [ ] **Step 1: Add CLI**

`tools/prepare_real_source_local_bundle.py` must parse `--csv`, `--metadata`, `--decisions`, and `--retention-policy`. On success it prints sorted, indented JSON. On exception it must print sanitized JSON to stderr:

```json
{
  "status": "BLOCKED",
  "error": "LOCAL_REAL_SOURCE_BUNDLE_PREPARATION_FAILED",
  "csv_path": "LOCAL_PATH_REDACTED",
  "metadata_path": "LOCAL_PATH_REDACTED",
  "decisions_path": "LOCAL_PATH_REDACTED",
  "retention_policy_path": "LOCAL_PATH_REDACTED"
}
```

- [ ] **Step 2: Add CLI redaction test**

```python
def test_real_source_local_bundle_cli_outputs_redacted_json(tmp_path: Path):
    csv_path = valid_csv(tmp_path / "valid.csv")

    result = subprocess.run(
        [
            sys.executable,
            "tools/prepare_real_source_local_bundle.py",
            "--csv",
            str(csv_path),
            "--metadata",
            "configs/data/real-ohlcv-source-metadata-template.yaml",
            "--retention-policy",
            "configs/data/raw-data-retention-policy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["status"] == "BLOCKED"
    assert "LOCAL_PATH_REDACTED" in result.stdout
    assert str(tmp_path) not in result.stdout
```

- [ ] **Step 3: Add validator**

`tools/validate_phase19.py` must:
- run `python tools/validate_phase18.py`
- run `python -m pytest tests/research/test_real_source_local_bundle.py -q`
- validate a blocked/default CLI scenario against `schemas/real_source_local_bundle.schema.json`
- assert CLI output does not contain local CSV, metadata, decisions, retention-policy, `C:\`, or `/Users/` paths
- assert `python tools/real_data_readiness.py` remains `BLOCKED`
- print `Phase 19 artifacts validated`

- [ ] **Step 4: Add validator test**

```python
def test_phase19_validator_runs_successfully():
    result = subprocess.run(
        [sys.executable, "tools/validate_phase19.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Phase 19 artifacts validated" in result.stdout
```

- [ ] **Step 5: Run validator tests**

Run: `python -m pytest tests/research/test_phase19_validator.py -v`

Expected: PASS.

---

### Task 5: Documentation, Agent Exchange, and Final Verification

**Files:**
- Create: `docs/implementation-reports/phase-19-local-only-real-source-bundle.md`
- Modify: `agent-exchange/inbox/human/2026-08-31T090000Z-human-real-data-decisions.md`
- Create: `agent-exchange/status/YYYY-MM-DDTHHMMSSZ-codex-phase-19-implementation-status.md`

**Interfaces:**
- Consumes: implementation and validation outputs from Tasks 1-4.
- Produces: operator-facing docs and Codex status record.

- [ ] **Step 1: Update human inbox**

Add the command:

```bash
python tools/prepare_real_source_local_bundle.py --csv <local_csv_path> --metadata <metadata_yaml_path> --decisions <decisions_yaml_path> --retention-policy <retention_policy_yaml_path>
```

Add this warning:

```text
The Phase 19 local bundle CLI is sanitized and local-only. It may produce redacted manifest metadata, but it does not approve raw retention, dataset construction, model training, model promotion, live trading, broker execution, or capital allocation.
```

- [ ] **Step 2: Write implementation report**

The report must include:
- scope
- files
- tests
- decisions
- unresolved risks
- next phase

It must explicitly state that Phase 19 does not run dry-run or train a model.

- [ ] **Step 3: Run focused verification**

Run:

```bash
python -m pytest tests/research/test_real_source_local_bundle.py tests/research/test_phase19_validator.py -v
python tools/validate_phase19.py
python tools/real_data_readiness.py
```

Expected: tests pass, validator prints `Phase 19 artifacts validated`, readiness remains `BLOCKED`.

- [ ] **Step 4: Run full verification**

Run:

```bash
python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research tests/agent_exchange -q
foreach ($p in 0..19) { python "tools/validate_phase$p.py"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
python tools/real_data_readiness.py
python tools/real_data_readiness.py --decisions configs/research/real-data-decisions-template.yaml
git diff --check
python tools/watch_agent_exchange.py --once
```

Expected: all commands pass, readiness remains `BLOCKED`, and no production action is approved.

- [ ] **Step 5: Record Codex result**

Write an `IMPLEMENTED_AWAITING_CODEX_REVIEW` status file listing changed files, verification results, decisions needed, blockers, and recommended next action.

---

## Self-Review

- Spec coverage: covers the Phase 18 next step by defining a local-only real-source bundle preparation path while keeping production dataset/model gates closed.
- Placeholder scan: no placeholder terms or unspecified "add tests" steps remain.
- Type consistency: all tasks use `build_real_source_local_bundle`, `RealSourceLocalBundle`, `real_source_local_bundle.schema.json`, and `LOCAL_MANIFEST_PREPARED_PRODUCTION_BLOCKED` consistently.
- Known intentional limitation: Phase 19 does not create a production dataset and does not train a model. That belongs to later phases after explicit human decisions and a separate dataset gate.
