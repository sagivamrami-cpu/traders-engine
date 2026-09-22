# Bounded final-review fix

Request: controller-assigned final-review fix; the user's actual request was to
continue implementation. No separate reviewer message was available or assumed.
Read AGENTS.md, exchange README/protocol, the
Codex inbox (existing request already accepted), and the adapter plan Globals/Task 2.

Changed only:

- `tools/check_ema_source_parity.py`
- `tests/tree_replay/test_ema.py`
- `.superpowers/sdd/2026-09-09-asof-ema-adapter/final-fix-report.md`

The checker now validates the fixed audit scope before reading any source/vendor
file. It requires schema `chartdesk-ema-contracts-v1`, repository `chart-desk`, and
commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, also matching the chart-desk
baseline pin. Exactly three unique source rows are required; empty lists, omitted,
duplicate or unknown files cannot yield verification success.

| Required source | Vendor path | Exact unique symbols |
| --- | --- | --- |
| `chartdesk/indicators.py` | `trading_system/tree_replay/_vendor/indicators.py` | `_seeded_recursive`, `ema`, `stdev` |
| `chartdesk/tr.py` | `trading_system/tree_replay/_vendor/tr.py` | `TR_EMAS`, `emas`, `ema_cloud` |
| `chartdesk/features.py` | explicit null | empty list |

Expected imports are also fixed: future annotations/numpy as np/pandas as pd for
indicators; future annotations/pandas as pd/relative indicators as I for tr; none
for features. Import AST comparison permits spacing/comments and ordering changes
but rejects duplicate declarations, extra code, missing or unknown imports. A
matching manifest/vendor import expansion cannot widen this scope. Blob fields
must be 40 lowercase hexadecimal characters. Malformed coverage fields return
explicit CONTRACT_* blockers. Existing source hash, selected AST, vendor imports
and unexpected-top-level checks still run after contract validation succeeds.

Synthetic fixtures now contain the complete required identity and file/symbol/
import coverage, with tiny synthetic bodies and locally computed fixture hashes.
They do not use the retained checkout or any external dependency. The source-only
features fixture raises if executed; selected synthetic functions also contain
raising bodies. The checker only reads text, hashes and parses ASTs.

## Exact verification

Used the test-driven-development and verification-before-completion skills to
observe regressions before implementation and verify results before handoff.

1. Initial RED, after replacing the fixture and adding the first 32 regressions:
   `python -m pytest tests/tree_replay/test_ema.py -q`
   Exit 1: **31 failed, 33 passed in 12.29s**. All original 32 cases passed;
   the existing mismatched-commit behavior already passed its new regression.
2. Expanded RED, adding malformed scope and direct CLI coverage before the fix:
   `python -m pytest tests/tree_replay/test_ema.py -q --tb=line`
   Exit 1: **46 failed, 34 passed in 2.58s**. The second already-passing new
   case was a changed baseline commit. Failures included false success for empty,
   omitted and duplicate files/symbols, absent contract-level blockers, and uncaught
   KeyError/TypeError on malformed fields. The CLI reproduction with `files=[]`
   and a nonexistent source root returned 0 where the test required 2.
3. GREEN, after implementing validation:
   `python -m pytest tests/tree_replay/test_ema.py -q`
   Exit 0: **80 passed in 2.31s** (32 original + 48 added cases). The CLI
   reproduction now returns 2 with source verification and both readiness flags
   false. After this run, only the validator docstring was clarified and this
   report was added; executable code and tests were unchanged.
4. Retained-source CLI:
   `python tools/check_ema_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk`
   Exit 0: `blockers=[]`, `source_subset_verified=true`, source commit
   `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`, `ready_for_replay=false`,
   `ready_for_training=false`.

No broader suite was run. No source checkout execution/import, network calls,
subagents, schema framework, commits, inbox edits or parent status/docs edits.

## Contract limits

This validates the fixed coverage/identity portion of trusted configuration.
Manifest blob hash values remain trusted inputs, not an independently authenticated
registry: coordinated edits to a source body, vendor body and corresponding
manifest hash can still match. The tool does not verify checkout HEAD, prove
blob membership in Git history, or protect against modification of the checker
itself. Source text retains the existing CRLF-to-LF normalization for hashing.

The consumer and observation descriptions elsewhere in the manifest are not
schema-validated here. Features.py is required and verified by its full-file blob,
with no vendored symbols or imports. Selected AST identity and numerical fixtures
do not certify full replay, live unfinished-bar behavior, candidate generation,
market labels, training or production deployment. All readiness flags remain false.

No blockers remain for this bounded fix. Parent handles final acceptance and
shared status/documentation updates.
