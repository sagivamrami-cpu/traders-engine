# Agent Exchange Review

Reviewer: Independent Codex whole-component reviewer; no nested agents

Target request: agent-exchange/inbox/codex/2026-09-09T213600Z-revalidation-final-review.md

Created at: 2026-09-09T21:37:25Z

Status: REVIEW_READY_FOR_CODEX

Verdict:

- Spec compliance: PASS for the complete six-file revalidation component.
- Code quality: Approved. No Critical, Important, or Minor findings.
- Ready to merge/integrate: Yes for this scoped offline component, subject to main-owned acceptance. This is not full replay or model certification.

Findings:

### Strengths and whole-component alignment

- The implementation matches the contract's complete policy projection. `trading_system/tree_replay/_vendor/revalidation.py:84` constructs actual TrackerAdmission, StretchReader and EmaReader over one supplied source. `:187` preserves bias-flip precedence and distinct send-bias labels; `:204` retains the same-direction stretch veto; `:215` retains separate age requests, operation clocks, normalization, oldest evidence and exception reset. These are actual calculations, with controlled raw tree replies confined to the explicitly unbound boundary.
- `trading_system/tree_replay/_vendor/revalidation.py:234` keeps EMA, session, stop-distance, structure, vector and news shadows observational. `:136` preserves ensure/open/time/JSON/write/close behavior and swallowed failures. `:113` keeps initial validation before the default pending clock, the exact two-hour boundary, opposing-tree precedence and preservation of prior verification. Calendar helpers at `:18` and `:46` retain numeric precedence, raw timezone/nonfinite behavior, inclusive windows and input-order/impact semantics.
- Task2 independently reconstructs the same imports, constants, helpers, constructor and method ordering: `trading_system/tree_spec/revalidation_source.py:19`, `:35`, `:44`, `:70`, `:134`. Literal pins, root/HEAD/baseline checks, exact-one substitutions and fifteen shadow-name substitutions agree with Task1 and the contract. The comparison includes the entire ordered runtime AST, removing only its module docstring.
- `trading_system/tree_spec/revalidation_source.py:141` invokes all seven required real audits. Dependency blockers survive even inconsistent verification flags; false-with-empty-blockers and supported audit input errors also block. Nested EMA/range closure was independently probed below. Static inspection confirmed session tables/helpers, matrix/toolkit dependencies, complete lifecycle voice, and the default non-auction PVSRA projection are included by the inherited audits. `_higher_bias` requires both requested higher-frame views and consumes their actual `.net` values (`trading_system/tree_replay/_vendor/tracker_admission.py:242`).
- Runtime tests use OHLC/volume frames, calculated TFViews, real range/EMA/structure/PVSRA calculations, and an in-memory JSON writer (`tests/tree_replay/test_revalidation.py:29`, `:46`, `:322`, `:363`, `:377`, `:394`). Auditor tests exercise identity, order, policy mutations, every immediate consumed dependency, inconsistent dependency reports and import isolation (`tests/tree_spec/test_revalidation_source.py:41`, `:103`, `:139`, `:153`, `:185`). The two layers test complementary behavioral and source-equivalence properties.
- `docs/architecture/REVALIDATION-SOURCE-USAGE.md:18`, `:34`, `:59` correctly describe the raw ports, unknown-state limits and unbound tree. `tools/check_revalidation_source_parity.py:13` requires explicit source-root input and emits JSON with VERIFIED/0 or BLOCKED/2. Both readiness flags remain false. The prerequisite EMA/deep component is explicitly ACCEPTED_BY_CODEX in `agent-exchange/status/2026-09-09T211034Z-codex-ema-deep-reader.md`.

### Issues

- Critical: None.
- Important: None.
- Minor: None.
- No deferred or parked findings.

Open questions:

None within this component. Full tree_walk, causal provider provenance and historical timezone, caller/lifecycle/effects, remaining producers and economics/data/model work remain explicit master-plan obligations, not defects hidden by this approval. Main retains acceptance and readiness decisions.

Recommended next action:

Record main-owned component acceptance and update its ledger/status documentation; continue the disjoint full-tree source intake. No component revision requested.

Verification reviewed:

- Read startup AGENTS/exchange README/protocol, inspected the Codex inbox, and read the final request, contract, current plan, both complete task diffs, both task briefs, Task2 report, ledger, runtime/auditor status reports, both task reviews and their original requests, and the EMA acceptance record. Applied the supplied `requesting-code-review/code-reviewer.md` rubric directly. No nested agents or broad repository/source crawl.
- `git rev-parse HEAD`: `c1b6071633c55376c64f0a98ece843706f420f49`, matching the review base. Inspected `git status --short`, `git diff --stat`, and the six-path `git diff`. The six additions are untracked, so the complete supplied diffs are their review representation. Existing unrelated changes were left untouched.
- Independently parsed both packages with PowerShell, extracted each `+++ b/` target and added lines, and compared against `[System.IO.File]::ReadAllLines` with case-sensitive equality and exact line counts: all six MATCH. Final `Get-FileHash -Algorithm SHA256` confirmed unchanged files after the probes. Hashes below identify the exact reviewed state.

| File | SHA256 |
| --- | --- |
| trading_system/tree_replay/_vendor/revalidation.py | F11DC02C4CE8CE9E4CF7B387D8AE76FEBD8256D3B2559C985669534E227DE8D3 |
| tests/tree_replay/test_revalidation.py | 35AD02B24F5353667170088AEDE947155596E9BFAD51D0508CA2E2F3D1178328 |
| docs/architecture/REVALIDATION-SOURCE-USAGE.md | 1EFBB152234EB76D0AD646AC4EBDAC8C56CDF0897746588EB2D5F6DF638074EA |
| trading_system/tree_spec/revalidation_source.py | 815E33558B707744FC1E6D140C0C8B9737209669F5DF21286B24661184A9209A |
| tests/tree_spec/test_revalidation_source.py | FF4057D65B4B6CCBA1D5708BBB33058CF29D71A58E18BBD469C648A65D7D788A |
| tools/check_revalidation_source_parity.py | FB1C23F0ADEEC7C22B298EAD2770909F266993958E9229003BFA540D5B4A21F8 |

- Runtime/test/usage hashes match the runtime report. Auditor/CLI hashes match the auditor progress report. The audit-test hash differs from the earlier 59-case snapshot because of the four documented test-only additions; its current 201 lines exactly match the complete Task2 package.
- Reported verification, not rerun: Task1 missing-module RED (50), subsequent 77 focused cases and 370 planned cases; Task2 missing-auditor RED (59), then 59 passed in 99.45s, plus four added cases passed with 59 deselected in 7.59s. Main's reported in-memory behavioral mutations disabled the send-bias veto and changed the news window to 15 minutes; both raised AssertionError. These are reviewed records, not new independent executions.
- Current combined command reported in `task-2-report.md`: `python -B -m pytest tests/tree_replay/test_revalidation.py tests/tree_spec/test_revalidation_source.py tests/tree_replay/test_ema_windows.py tests/tree_replay/test_stretch.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_calculations.py tests/tree_replay/test_lifecycle_bars.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_watch_storage.py -q --tb=short -p no:cacheprovider` — **539 passed, 114.26s, exit 0**, session80757 terminal, unchanged files during the run. Not repeated, and overlapping test counts are not added together. The earlier nonexistent lifecycle-test filename was corrected before this successful run.
- Concrete cross-task doubt: immediate dependency mutation tests might miss a nested numerical module used by the actual composed readers. Static inspection established strict EMA and range audit calls; the following two independent in-memory mutations then confirmed propagation to the whole-component verdict. PASS, exit 0, 6.26s. Both produced BLOCKED with false readiness; indicator drift appeared under both stretch/EMA and ema_windows/EMA, and range drift under stretch/range. No file mutation, retained-source execution, runtime import or suite run occurred.

```powershell
@'
import sys
from pathlib import Path
from unittest.mock import patch
class Guard:
    def find_spec(self, fullname, *args):
        if fullname.startswith(('chartdesk', 'floor', 'trading_system.tree_replay')):
            raise AssertionError('forbidden execution import: ' + fullname)
sys.meta_path.insert(0, Guard())
from trading_system.tree_spec.revalidation_source import audit_revalidation_source
root = Path('C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149')
vendor = Path('trading_system/tree_replay/_vendor').resolve()
original = Path.read_text
for filename, prefixes in [
    ('indicators.py', ('DEPENDENCY:ema_windows:DEPENDENCY:ema:', 'DEPENDENCY:stretch:DEPENDENCY:ema:')),
    ('ranges.py', ('DEPENDENCY:stretch:DEPENDENCY:range:',)),
]:
    target = vendor / filename
    def intercepted(path, *args, **kwargs):
        text = original(path, *args, **kwargs)
        return text + '\nREVIEW_DRIFT = True\n' if path.resolve() == target else text
    with patch.object(Path, 'read_text', intercepted):
        report = audit_revalidation_source(root)
    assert report['status'] == 'BLOCKED' and not report['source_subset_verified'], report
    assert not report['ready_for_replay'] and not report['ready_for_training']
    for prefix in prefixes:
        assert any(b.startswith(prefix) for b in report['blockers']), report['blockers']
    print('PASS nested mutation:', filename)
    for blocker in report['blockers']:
        if any(blocker.startswith(prefix) for prefix in prefixes):
            print(blocker)
assert not any(n.startswith(('chartdesk', 'floor', 'trading_system.tree_replay')) for n in sys.modules)
print('PASS source/runtime import guard; no on-disk mutation; two named probes only')
'@ | python -B -
```

Reviewer tooling note: one static-read command used unsupported shell brace expansion and failed at PowerShell parsing; it was corrected with explicit paths. No product code ran in that failed command. Only this requested review report was written, via apply_patch.

Assessment: Approved. Real runtime composition and independently pinned whole-module/dependency checks align with the agreed scope, with meaningful behavior and mutation evidence and explicit unbound boundaries.
