import json
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "gc_tree_translation_gap_review_fixture",
    ROOT / "tests/models/test_gc_tree_translation_gap_review.py",
)
if _FIXTURE_SPEC is None or _FIXTURE_SPEC.loader is None:
    raise RuntimeError("tree translation gap review fixture could not be loaded")
_FIXTURE_MODULE = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURE_MODULE)
walk_forward_run = _FIXTURE_MODULE.walk_forward_run


def test_gc_tree_translation_gap_review_cli_writes_sanitized_review(tmp_path: Path):
    run_path = tmp_path / "walk-forward-run.json"
    review_out = tmp_path / "tree-gap-review.json"
    run_path.write_text(json.dumps(walk_forward_run()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/gc_tree_translation_gap_review.py",
            "--walk-forward-run",
            str(run_path),
            "--review-out",
            str(review_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "TREE_TRANSLATION_REDESIGN_REQUIRED"
    assert payload["additional_model_training_allowed"] is False
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert json.loads(review_out.read_text(encoding="utf-8")) == payload
    assert result.stderr == ""
