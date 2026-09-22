import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-identity.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_dataset_identity_manifest.schema.json"
CREATED_AT = datetime(2026, 9, 2, 14, 30, tzinfo=UTC)
OHLCV_SHA = "b59a9dd08a317162024d53c4f0841a68d68e51dfb66f5d9d62b140304c24c3d1"
OF_SHA = "34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155"


def validate_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_identity_is_deterministic_and_independent_of_created_at():
    from trading_system.research.gc_dataset_identity import build_gc_dataset_identity

    first = build_gc_dataset_identity(CONFIG_PATH, created_at=CREATED_AT).to_payload()
    second = build_gc_dataset_identity(CONFIG_PATH, created_at=datetime(2030, 1, 1, tzinfo=UTC)).to_payload()
    validate_payload(first)
    assert first["dataset_id"] == second["dataset_id"]
    assert first["manifest_id"] != second["manifest_id"]
    assert first["identity_source"] == "CANONICAL_MANIFEST_DECLARED"
    assert first["dataset_identity_gate_status"] == "SATISFIED_DETERMINISTIC_IDENTITY_V1"
    assert first["blocked_reasons"] == []
    assert first["input_archives"]["ohlcv_1s"]["sha256"] == OHLCV_SHA
    assert first["input_archives"]["order_flow_1m"]["sha256"] == OF_SHA
    assert first["input_archives"]["order_flow_1m"]["selected_member"] == "gc/GCext_of_1m.parquet"
    assert "configs/datasets/gc-30m-real-dataset-contract.yaml" not in first["config_hashes"]
    assert "configs/data/gc-missing-bar-policy.yaml" in first["config_hashes"]
    assert first["rules"]["horizon_bars"] == 8
    assert first["dataset_construction_allowed"] is False
    assert first["training_allowed"] is False


def test_identity_changes_when_a_governing_config_changes(tmp_path: Path):
    from trading_system.research.gc_dataset_identity import build_gc_dataset_identity

    baseline = build_gc_dataset_identity(CONFIG_PATH, created_at=CREATED_AT).to_payload()
    # Copy the repo subset into tmp and mutate one governing config.
    for rel in (
        "configs/datasets/gc-30m-real-dataset-identity.yaml",
        "configs/data/session-calendar.yaml",
        "configs/data/gc-missing-bar-policy.yaml",
        "configs/data/gc-order-flow-row-mask-cumulative-policy.yaml",
        "configs/data/gc-canonical-ohlcv-input-manifest.yaml",
        "configs/data/gc-canonical-order-flow-input-manifest.yaml",
        "configs/models/baseline-training-policy.yaml",
        "schemas/gc_missing_bar_policy.schema.json",
        "schemas/gc_dataset_identity_manifest.schema.json",
        "schemas/candidate_training_row.schema.json",
        "schemas/gc_order_flow_row_mask_cumulative_policy.schema.json",
    ):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((ROOT / rel).read_text(encoding="utf-8"), encoding="utf-8")
    mutated = tmp_path / "configs/models/baseline-training-policy.yaml"
    mutated.write_text(mutated.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    changed = build_gc_dataset_identity(
        tmp_path / "configs/datasets/gc-30m-real-dataset-identity.yaml",
        created_at=CREATED_AT,
        root=tmp_path,
    ).to_payload()
    assert changed["dataset_id"] != baseline["dataset_id"]


def test_identity_verifies_local_archive_hashes_and_blocks_on_mismatch():
    from trading_system.research.gc_dataset_identity import build_gc_dataset_identity

    good = build_gc_dataset_identity(
        CONFIG_PATH,
        created_at=CREATED_AT,
        local_archive_hashes={
            "ohlcv_1s": {"sha256": OHLCV_SHA, "size_bytes": 984191105},
            "order_flow_1m": {"sha256": OF_SHA, "size_bytes": 2496805183},
        },
    ).to_payload()
    assert good["identity_source"] == "LOCAL_ARCHIVE_VERIFIED"
    assert good["input_archives"]["ohlcv_1s"]["verified_against_local_file"] is True
    bad = build_gc_dataset_identity(
        CONFIG_PATH,
        created_at=CREATED_AT,
        local_archive_hashes={
            "ohlcv_1s": {"sha256": "0" * 64, "size_bytes": 984191105},
            "order_flow_1m": {"sha256": OF_SHA, "size_bytes": 1},
        },
    ).payload
    assert "OHLCV_1S_LOCAL_ARCHIVE_SHA256_MISMATCH" in bad["blocked_reasons"]
    assert "ORDER_FLOW_1M_LOCAL_ARCHIVE_SIZE_MISMATCH" in bad["blocked_reasons"]
    assert bad["dataset_identity_gate_status"] == "UNSATISFIED"
    assert bad["identity_source"] == "CANONICAL_MANIFEST_DECLARED"
    # dataset_id is a function of the declared identity, not of verification outcome.
    assert bad["dataset_id"] == good["dataset_id"]


def test_identity_config_expected_hashes_match_canonical_manifests():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    for key in ("ohlcv_1s", "order_flow_1m"):
        spec = config["input_archives"][key]
        manifest = yaml.safe_load((ROOT / spec["canonical_manifest_ref"]).read_text(encoding="utf-8"))
        assert manifest["archive_sha256"] == spec["expected_sha256"]
        assert manifest["archive_size_bytes"] == spec["expected_size_bytes"]


def test_builder_rules_match_approved_label_split_policy():
    from trading_system.research import gc_real_dataset_builder as builder

    policy = yaml.safe_load((ROOT / "configs/research/gc-label-split-policy.yaml").read_text(encoding="utf-8"))
    label = policy["label_contract_policy"]
    split = policy["split_and_embargo_policy"]
    assert builder.TARGET_MULTIPLE == label["target_multiple"]
    assert builder.STOP_MULTIPLE == label["stop_multiple"]
    assert builder.HORIZON_BARS == label["max_horizon_bars"]
    assert builder.EMBARGO_BARS == split["embargo_bars"]
    assert split["split_method"] == "CHRONOLOGICAL_WALK_FORWARD_ONLY"
    assert split["random_split_allowed"] is False
    assert label["entry_availability"] == "NEXT_BAR_OPEN_AFTER_DECISION_BAR_CLOSE"


def test_identity_cli_outputs_sanitized_json():
    result = subprocess.run(
        [sys.executable, "tools/build_gc_dataset_identity.py", "--config", "configs/datasets/gc-30m-real-dataset-identity.yaml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    validate_payload(payload)
    assert payload["dataset_identity_gate_status"] == "SATISFIED_DETERMINISTIC_IDENTITY_V1"
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""
