### Spec Compliance

- Issues found: **I1** — dependency errors do not always become blockers; a missing chart-desk baseline pin escapes as `StopIteration` (`trading_system/tree_spec/tree_walk_source.py:193`, `:198`). This violates the dependency-error requirement and prevents the CLI's JSON/2 result (`tools/check_tree_walk_source_parity.py:17`).
- Cannot verify from this diff: candidate-execution mutation probes `61395e` and `a5f354` are reported but their code/output is not included in the three-file package (`.superpowers/sdd/2026-09-10-tree-walk-reader/task-2-report.md:21`). Controller should retain those probe artifacts. The combined command, Task1 test fix, final review and documentation/master acceptance remain separate; no verdict on them is issued.

Reviewer: Codex independent Task2 reviewer

Request: agent-exchange/inbox/codex/2026-09-10T192830Z-tree-walk-audit-review.md

Created at: 2026-09-10 19:30:08 UTC

Status: REVIEW_READY_FOR_CODEX

Scope: Task2's three frozen additions only; BASE=HEAD=c1b6071633c55376c64f0a98ece843706f420f49. Required task-reviewer-prompt.md applied. Brief, report, then complete diff read in order; changed files were not separately reread. Startup AGENTS/readme/protocol/inbox and required status/diff inspection completed. No nested agents, commits, runtime edits, original-source execution, data or live actions.

### Strengths

- Independent literal commit/blob authority, ordered inventory including both FINAL_STAGE assignments and tuple assignment, six signatures, constructor and imports establish a candidate-independent projection (`trading_system/tree_spec/tree_walk_source.py:17`, `:23`, `:99`). Exact-count substitutions use the inherited AST helper; complete ordered AST comparison retains bodies, docstrings and statement positions (`:112`, `:125`, `:173`; `trading_system/tree_spec/tracker_admission_source.py:152`).
- The real eight-auditor graph is invoked with explicit parent versus chart-desk roots. Child blocker strings are preserved and nonverified empty reports are blocked; both readiness fields remain false (`trading_system/tree_spec/tree_walk_source.py:140`, `:186`). Named dependency-coverage inspection confirmed pricing/map sessions through levelmap, and calendar/watch sessions through revalidation/watch IO (`tools/check_levelmap_source_parity.py:35`, `:73`; `trading_system/tree_spec/revalidation_source.py:72`, `:141`; `trading_system/tree_spec/watch_io_source.py:59`).
- Mutation tests cover full candidate AST drift, source authority/inventory, missing/syntax failures, all eight dependency reports and actual transitive drift. CLI tests cover unrelated working directories, invalid roots and forbidden imports (`tests/tree_spec/test_tree_walk_source.py:39`, `:85`, `:101`, `:153`, `:165`, `:176`).

### Issues

#### Critical (Must Fix)

None found.

#### Important (Should Fix)

**I1 — A missing baseline pin bypasses the blocked-report boundary.**

References: `trading_system/tree_spec/tree_walk_source.py:156`, `:193`, `:198`; `tools/check_ema_source_parity.py:92`; `trading_system/tree_spec/tracker_admission_source.py:130`; `tools/check_tree_walk_source_parity.py:17`; `tests/tree_spec/test_tree_walk_source.py:153`.

The top-level baseline check correctly records BASELINE_COMMIT_MISMATCH when the chart-desk row is absent, then continues through the actual dependency graph. The EMA auditor obtains that same row with `next(...)` without a default. Its `StopIteration` is outside INPUT_ERRORS, so it escapes `audit_tree_walk_source` and discards the already accumulated report. The CLI consequently raises instead of printing BLOCKED JSON and returning 2. The existing dependency-error test only raises OSError and misses this real dependency failure.

Reproduced with one process-local Path.read_text interception that removed only the chart-desk row from the baseline JSON; all actual auditors ran, all on-disk files remained unchanged. Observed traceback: `tree_walk_source.py:193 -> check_ema_source_parity.py:92 -> StopIteration`. Probe printed `MISSING_BASELINE_PIN_ESCAPED=StopIteration`; its shell exit 0 came from the diagnostic catch, not an auditor pass.

Fix the Task2 dependency boundary to normalize this known missing-pin exception into a named dependency blocker while retaining existing blockers and false readiness. Add a focused regression using the actual EMA auditor and missing baseline row, checking returned BLOCKED status and CLI JSON/2 where practical. This does not require changing Task1 runtime or executing original sources.

#### Minor (Nice to Have)

None raised. The report explicitly separates Git CRLF normalization notices from warning-free pytest output; no pytest-warning finding is inferred.

### Verification reviewed

- Reported, not rerun: `python -B -m pytest tests/tree_spec/test_tree_walk_source.py -x -q --tb=short -p no:cacheprovider` — 71 passed, 309.85s, exit 0; reported standalone explicit-root CLI VERIFIED/0 (`.superpowers/sdd/2026-09-10-tree-walk-reader/task-2-report.md:12`). Combined verification remains controller-owned.
- Independent named-risk checks: read the shared exact-count/error helper for projection-boundary risk; traced actual pricing/session dependency edges for missing-transitive-coverage risk; inspected the EMA baseline lookup and ran the single missing-pin probe for uncaught-dependency-error risk. No suite rerun or Task1 runtime review.
- Exact targeted probe, supplied to `python -B -` through a PowerShell literal here-string; result **FAIL** for the required blocked-report behavior:

```python
import json
from pathlib import Path
from unittest.mock import patch
from trading_system.tree_spec.tree_walk_source import audit_tree_walk_source
root = Path('C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149')
baseline = Path('configs/trees/existing-alerts-baseline.json').resolve()
read = Path.read_text
def missing_pin(path, *args, **kwargs):
    text = read(path, *args, **kwargs)
    if path.resolve() == baseline:
        doc = json.loads(text)
        doc['repositories'] = [row for row in doc['repositories'] if row['name'] != 'chart-desk']
        return json.dumps(doc)
    return text
with patch.object(Path, 'read_text', missing_pin):
    try:
        report = audit_tree_walk_source(root)
    except Exception as exc:
        import traceback
        print('MISSING_BASELINE_PIN_ESCAPED=' + type(exc).__name__)
        traceback.print_exc()
    else:
        print(json.dumps({'status': report['status'], 'blockers': report['blockers']}))
```

- `Get-FileHash trading_system/tree_spec/tree_walk_source.py,tools/check_tree_walk_source_parity.py,tests/tree_spec/test_tree_walk_source.py` — **PASS**, before/after checks match the frozen report:

| File | SHA256 |
| --- | --- |
| trading_system/tree_spec/tree_walk_source.py | 537731443E1E828AA872728B44BF6A3FB9922E8606227A010DA53C77ACF25D29 |
| tools/check_tree_walk_source_parity.py | 0C740DFC3B387C2D49DB596B3C12C98BA8F29446FE095076698BC9F504AB7A68 |
| tests/tree_spec/test_tree_walk_source.py | 5CF46527C847D9C0B779E6D60BA43C031B9D4F4773C62C22DD4278ACDD7F9008 |

### Assessment

**Task quality: Needs fixes.** The independent ordered projection and actual graph coverage are well structured, but the demonstrated dependency exception violates the auditor/CLI failure contract. Resolve I1 before Task2 acceptance.

Open questions: No human decision needed for I1. Controller retains ownership of the separately pending combined evidence and behavior-probe artifacts.

Recommended next action: Fix I1 within Task2, supply focused regression evidence and updated hashes, then request scoped re-review. No whole-master, historical replay, economics, dataset or model acceptance is implied.

### Scoped I1 re-review — 2026-09-10 19:33:28 UTC

**I1: ADDRESSED. Spec compliance: PASS for the scoped fix; the previous Task2 blocking finding is closed. Task quality: Approved for Task2.** This addendum supersedes the earlier Needs fixes verdict for I1; combined/final acceptance remains separate.

- Reviewed `.superpowers/sdd/2026-09-10-tree-walk-reader/task-2-fix-report.md` and `task-2-fix-diff.md` against the unchanged brief and I1. The dependency boundary now catches the known `StopIteration` alongside INPUT_ERRORS and appends a named blocker (`trading_system/tree_spec/tree_walk_source.py:198`). It retains previously collected blockers, continues dependency processing and leaves readiness false; it introduces no blanket exception catch or runtime change.
- The two new regression cases remove the chart-desk baseline row through process-local text interception while retaining the actual EMA dependency. They exercise the API and actual `CLI.main()`, assert BLOCKED/nonverified, preservation of BASELINE_COMMIT_MISMATCH, the EMA StopIteration blocker, false readiness, and parsed CLI JSON with return code 2 (`tests/tree_spec/test_tree_walk_source.py:109`). They directly cover the demonstrated failure, rather than substituting a fake child exception.
- Verification reviewed, not rerun: `python -B -m pytest tests/tree_spec/test_tree_walk_source.py -k missing_baseline_pin -q --tb=short -p no:cacheprovider` — reported RED 2 failed/71 deselected in 9.38s, then GREEN 2 passed/71 deselected in 9.29s, exit 0 (`.superpowers/sdd/2026-09-10-tree-walk-reader/task-2-fix-report.md:4`). No new doubt warranted another test run.
- Independent `Get-FileHash` check: all three current SHA256 values match the fix report. Auditor: `7A365D7711EC298BFAE6BE8BE4C20FC4E4118745B12EF788B44C5E0FD67E30D9`; unchanged CLI: `0C740DFC3B387C2D49DB596B3C12C98BA8F29446FE095076698BC9F504AB7A68`; tests: `97E66C21906751AFC3F8FD0CFB187DAEA36A640CD530CD62B31866BC31097DAD`.
- New findings: none. The narrow exception normalization and actual-dependency regressions resolve I1 without expanding the task. The main inline fix is consistent with the supplied plan authorization.
- Scope limits: amended combined run 81419 was reported running; no terminal pass is claimed here. Behavior-probe artifacts are being retained separately for final review. Task1, those artifacts and whole-master acceptance were not reopened. No suite reruns, nested agents, runtime edits or other file changes were made by this reviewer.

Recommended next action: Controller may close I1 and proceed with the separately owned combined verification and final review.
