### Task 8: Full Phase 0 Validation Command

**Files:**
- Modify: `tests/specification/test_phase0_configs.py`

**Interfaces:**
- Consumes: `tools.validate_phase0.main`.
- Produces: one full validation check covering schemas and required Phase 0 artifacts.

- [ ] **Step 1: Add full validation test**

Append to `tests/specification/test_phase0_configs.py`:

```python
from tools.validate_phase0 import main as validate_phase0_main


def test_full_phase0_validation_command(capsys):
    assert validate_phase0_main() == 0
    assert "Phase 0 artifacts validated" in capsys.readouterr().out
```

- [ ] **Step 2: Run the full validation test**

Run: `python -m pytest tests/specification/test_phase0_configs.py::test_full_phase0_validation_command -v`

Expected: pass.

- [ ] **Step 3: Run all specification tests**

Run: `python -m pytest tests/specification -v`

Expected: all tests pass.

- [ ] **Step 4: Run validator CLI**

Run: `python tools/validate_phase0.py`

Expected:

```text
Phase 0 artifacts validated
```

- [ ] **Step 5: Commit**

```bash
git add tests/specification/test_phase0_configs.py
git commit -m "test: validate complete phase 0 artifact set"
```
