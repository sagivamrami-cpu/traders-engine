### Task 1: Test and Validation Tooling

**Files:**
- Modify: `requirements.txt`
- Create: `pytest.ini`
- Create: `tests/specification/test_phase0_tooling.py`

**Interfaces:**
- Consumes: existing Python environment.
- Produces: pytest discovery and imports for `yaml` and `jsonschema`.

- [ ] **Step 1: Write the failing test**

Create `tests/specification/test_phase0_tooling.py`:

```python
def test_phase0_validation_dependencies_import():
    import jsonschema
    import yaml

    assert jsonschema.Draft202012Validator.META_SCHEMA["$schema"].endswith("/schema")
    assert yaml.safe_load("phase: 0\n") == {"phase": 0}
```

- [ ] **Step 2: Run the test to verify it fails before dependencies are installed**

Run: `python -m pytest tests/specification/test_phase0_tooling.py -v`

Expected before dependency update: import failure for `pytest`, `jsonschema`, or `yaml` in a clean environment.

- [ ] **Step 3: Add dependencies and pytest configuration**

Append to `requirements.txt`:

```text
pytest>=8.0
PyYAML>=6.0
jsonschema>=4.22
```

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 4: Install dependencies**

Run: `python -m pip install -r requirements.txt`

Expected: command exits 0.

- [ ] **Step 5: Run the tooling test**

Run: `python -m pytest tests/specification/test_phase0_tooling.py -v`

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini tests/specification/test_phase0_tooling.py
git commit -m "test: add phase 0 validation tooling"
```
