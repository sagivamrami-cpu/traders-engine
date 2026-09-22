def test_phase0_validation_dependencies_import():
    import jsonschema
    import yaml

    assert jsonschema.Draft202012Validator.META_SCHEMA["$schema"].endswith("/schema")
    assert yaml.safe_load("phase: 0\n") == {"phase": 0}
