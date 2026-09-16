import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/sources/tr-hybrid-intelligence-tree.html"
MANIFEST = SOURCE.with_suffix(".manifest.json")


def load(path=SOURCE, **kwargs):
    from trading_system.tree_spec.catalog import load_catalog

    return load_catalog(path, **kwargs)


def altered_source(tmp_path, old, new):
    original = SOURCE.read_text(encoding="utf-8")
    assert old in original, "fixture change must target actual source content"
    path = tmp_path / "source.html"
    path.write_text(original.replace(old, new, 1), encoding="utf-8")
    return path


def test_all_guide_sections_are_retained_without_claiming_atomic_coverage():
    catalog = load()
    assert catalog.readiness()["section_counts"] == {
        "layers": 22, "trRows": 14, "trKnowledgeRows": 12,
        "sharedRows": 8, "ofRows": 18, "optionsRows": 19,
        "runtimeRows": 15, "governanceRows": 8,
    }
    assert len(catalog.units) == 116
    assert len({unit.unit_id for unit in catalog.units}) == 116
    assert catalog.readiness()["atomic_feature_coverage_verified"] is False


def test_questions_checks_and_source_locations_survive_import():
    catalog = load()
    unit = next(u for u in catalog.units if u.unit_id == "guide:layers:2")
    assert unit.question == "מהו כיוון הייחוס בכל timeframe והאם ה‑timeframes מסכימים?"
    assert "EMA 5/13/50/200/800" in unit.checks
    assert "stack, slope, separation, compression" in unit.checks
    assert unit.kind == "ALPHA EVIDENCE"
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    for item in catalog.units:
        evidence = "\n".join(lines[item.line_start - 1:item.line_end])
        assert item.title in evidence
        assert item.question in evidence


def test_open_parameters_and_incomplete_implementation_block_readiness():
    catalog = load()
    assert len(catalog.open_parameters) == 13
    assert "trigger definition" in catalog.open_parameters
    assert "RR_min by graph/style/version" in catalog.open_parameters
    report = catalog.readiness()
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
    assert "EXECUTABLE_TREE_NOT_IMPLEMENTED" in report["blockers"]
    assert "ATOMIC_CONTRACTS_NOT_VALIDATED" in report["blockers"]
    assert "OPEN_RESEARCH_PARAMETERS" in report["blockers"]


def test_manifest_hash_accepts_original_and_rejects_changed_source(tmp_path):
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))["sha256"]
    assert load(expected_sha256=expected).source_sha256 == expected
    path = altered_source(tmp_path, "EMA 5/13/50/200/800", "EMA 5/13/50")
    with pytest.raises(ValueError, match="hash"):
        load(path, expected_sha256=expected)


@pytest.mark.parametrize(("old", "new"), [
    ("var ofRows = [", "var missingOfRows = ["),
    ("var ofRows = [", "var ofRows = []; var ofRows = ["),
    ('{ title:"L0', '{ title:execute(), other:"L0'),
    ('["0 · DATA GATE",', '[execute(),'),
    ('["0 · DATA GATE",', '["0 · DATA GATE", 3,'),
    ('var layers = [', 'var layers = [ { title: "extra" },'),
    ('Vector baseline/threshold; Vector confirmation/recovery;', 'Vector baseline/threshold;'),
])
def test_unsupported_or_incomplete_source_is_rejected(tmp_path, old, new):
    with pytest.raises(ValueError):
        load(altered_source(tmp_path, old, new))


def test_quoted_delimiters_are_not_executed_or_treated_as_end_of_array(tmp_path):
    path = altered_source(tmp_path, "clock, UTC, DST", "clock ]; [ text, UTC, DST")
    assert "clock ]; [ text" in load(path).units[0].checks


def test_unrelated_script_is_inert(tmp_path):
    path = altered_source(tmp_path, "<head>", "<head><script>throw Error('never execute')</script>")
    assert len(load(path).units) == 116


def test_cli_reports_inventory_but_exits_nonzero_when_readiness_is_required():
    command = [sys.executable, str(ROOT / "tools/inspect_tree_source.py")]
    inspected = subprocess.run(command, cwd=ROOT.parent, capture_output=True, text=True, encoding="utf-8")
    assert inspected.returncode == 0, inspected.stderr
    assert json.loads(inspected.stdout)["ready_for_training"] is False
    blocked = subprocess.run(command + ["--require-ready"], capture_output=True, text=True, encoding="utf-8")
    assert blocked.returncode == 2
    full = subprocess.run(command + ["--include-units"], capture_output=True, text=True, encoding="utf-8")
    assert full.returncode == 0, full.stderr
    assert len(json.loads(full.stdout)["units"]) == 116


@pytest.mark.parametrize("digest", [None, "", "not-a-hash", "f" * 63, 123, []])
def test_cli_cannot_disable_integrity_verification_with_invalid_manifest_hash(tmp_path, monkeypatch, capsys, digest):
    from tools import inspect_tree_source

    sources = tmp_path / "docs/sources"
    sources.mkdir(parents=True)
    (sources / SOURCE.name).write_bytes(SOURCE.read_bytes())
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["sha256"] = digest
    (sources / MANIFEST.name).write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(inspect_tree_source, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["inspect_tree_source.py"])
    assert inspect_tree_source.main() == 1
    output = capsys.readouterr()
    assert not output.out
    assert "hash" in json.loads(output.err)["error"]
