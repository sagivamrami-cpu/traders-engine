import json
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_DATASET_SPEC = importlib.util.spec_from_file_location(
    "first_real_model_cli_fixture",
    ROOT / "tests/models/test_train_gc_first_real_model_cli.py",
)
if _DATASET_SPEC is None or _DATASET_SPEC.loader is None:
    raise RuntimeError("first real model CLI fixture could not be loaded")
_DATASET_MODULE = importlib.util.module_from_spec(_DATASET_SPEC)
_DATASET_SPEC.loader.exec_module(_DATASET_MODULE)
write_tiny_phase46_dataset = _DATASET_MODULE.write_tiny_phase46_dataset


def tree_gap_review() -> dict:
    return {
        "review_id": "a" * 64,
        "review_version": "gc-tree-translation-gap-review-0.1.0",
        "dataset_id": _DATASET_MODULE.DATASET_ID,
        "variant": "order_flow",
        "status": "TREE_TRANSLATION_REDESIGN_REQUIRED",
        "additional_model_training_allowed": False,
        "model_promotion_allowed": False,
    }


def test_gc_tree_gate_baseline_audit_cli_writes_sanitized_audit(tmp_path: Path):
    manifest_path, rows_root = write_tiny_phase46_dataset(tmp_path)
    review_path = tmp_path / "tree-gap-review.json"
    audit_out = tmp_path / "tree-gate-audit.json"
    review_path.write_text(json.dumps(tree_gap_review()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/gc_tree_gate_baseline_audit.py",
            "--build-manifest",
            str(manifest_path),
            "--rows-root",
            str(rows_root),
            "--tree-gap-review",
            str(review_path),
            "--variant",
            "order_flow",
            "--audit-out",
            str(audit_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "TREE_GATE_BASELINE_AUDIT_READY"
    assert payload["model_promotion_allowed"] is False
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(audit_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""
