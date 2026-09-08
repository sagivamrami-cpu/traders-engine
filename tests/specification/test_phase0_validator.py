from pathlib import Path

import pytest

from tools.validate_phase0 import (
    load_yaml,
    require_keys,
    validate_unique_ids,
    validate_research_parameter,
)


def test_require_keys_reports_missing_key():
    with pytest.raises(ValueError, match="missing required keys: version"):
        require_keys("sample", {"name": "x"}, ["name", "version"])


def test_validate_unique_ids_rejects_duplicates():
    with pytest.raises(ValueError, match="duplicate id: tr.vector"):
        validate_unique_ids("features", [{"id": "tr.vector"}, {"id": "tr.vector"}])


def test_validate_research_parameter_requires_status():
    with pytest.raises(ValueError, match="parameter missing required keys: status"):
        validate_research_parameter(
            {
                "parameter_id": "tr.vector.threshold",
                "hypothesis": "vector threshold requires evidence",
                "allowed_range": {"min": 0, "max": 1},
                "source": "research",
            }
        )


def test_load_yaml_reads_mapping(tmp_path: Path):
    path = tmp_path / "artifact.yaml"
    path.write_text("version: phase0-0.1.0\n", encoding="utf-8")
    assert load_yaml(path) == {"version": "phase0-0.1.0"}
