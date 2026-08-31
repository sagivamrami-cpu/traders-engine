from pathlib import Path

from trading_system.data_foundation.hashing import sha256_file
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.data_foundation.replay import build_phase1_dataset_payload

ROOT = Path(__file__).resolve().parents[2]


def test_replay_manifest_is_stable():
    assert build_phase1_dataset_payload(ROOT) == build_phase1_dataset_payload(ROOT)


def test_replay_manifest_counts_quality_statuses_separately():
    manifest = build_phase1_dataset_payload(ROOT)

    assert manifest["record_count"] == 6
    assert manifest["quality_status_counts"] == {
        "VALID": 2,
        "MISSING": 1,
        "STALE": 1,
        "CORRECTED": 1,
        "INVALID": 1,
        "UNKNOWN": 0,
    }


def test_replay_manifest_validates_against_schema():
    validate_json_payload(
        ROOT / "schemas/dataset_manifest.schema.json",
        build_phase1_dataset_payload(ROOT),
    )


def test_replay_fingerprint_changes_when_raw_hash_changes(tmp_path: Path):
    raw_file = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
    changed = tmp_path / "ohlcv_fixture.csv"
    changed.write_text(raw_file.read_text(encoding="utf-8").replace("450.00", "450.01", 1), encoding="utf-8")

    assert sha256_file(raw_file) != sha256_file(changed)


def test_replay_manifest_matches_expected_fixture():
    expected_path = ROOT / "tests/fixtures/data_foundation/expected/phase1_dataset_manifest.json"
    expected = expected_path.read_text(encoding="utf-8").strip()
    actual = __import__("json").dumps(build_phase1_dataset_payload(ROOT), sort_keys=True, separators=(",", ":"))

    assert actual == expected
