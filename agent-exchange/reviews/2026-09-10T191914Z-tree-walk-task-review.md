# Agent Exchange Review

Spec compliance: ISSUES FOUND — required Task1 test assertions are incomplete.
Task quality: NEEDS FIXES — test-contract gaps; no runtime source divergence found.

Reviewer: Codex independent Task1 reviewer
Request: agent-exchange/inbox/codex/2026-09-10T191914Z-tree-walk-task-review.md
Target request: agent-exchange/inbox/codex/2026-09-10T191914Z-tree-walk-task-review.md
Created at: 2026-09-10 19:22:04 UTC
Status: REVIEW_READY_FOR_CODEX

## Strengths

- All five required additions are present and match the report's SHA256 hashes and packaged diff. Parsed comparison of all six methods found only the enumerated bindings/import/clock substitutions. The core retains all 34 non-import nodes in order, including both FINAL_STAGE assignments; its only AST differences are the two permitted imports (`tree_core.py:102`, `tree_core.py:113`, `tree_core.py:218`; paths below are relative to `trading_system/tree_replay/_vendor/`).
- Actual dependency construction and the import-only signal facade satisfy the composition contract (`tree_walk.py:17`, `tree_signals.py:1`). Construction performed no raw reads in the focused probe. News captures its clock before calendar IO; session and provisional PSY use separate calls (`tree_walk.py:173`, `tree_walk.py:181`, `tree_walk.py:195`).
- Tests exercise actual house/strict walks, thirteen ordered pivots, mixed/neutral trends, raw W/M/RVC/GVC/Brinks evidence, drift, and both stop-clamp consumers (`tests/tree_replay/test_tree_walk.py:156`, `:268`, `:280`, `:324`, `:383`, `:413`, `:434`, `:452`, `:482`). Usage correctly distinguishes source pricing from admission/fills and defers causal certification (`docs/architecture/TREE-WALK-READER-USAGE.md:40`).

## Findings

### Important — I1: Required memory and ladder proof lacks outcome assertions

`tests/tree_replay/test_tree_walk.py:156`, `:367`, `:467`; requirements: `.superpowers/sdd/2026-09-10-tree-walk-reader/task-1-brief.md:44`, `:48`, `:53`.

The full-walk tests do not assert the raw-produced `w.zones` midpoint/kind/touch tuples or the memory facts/missing classification. The vector-anchor tests supply `Walk.zones` directly, bypassing the handoff at `trading_system/tree_replay/_vendor/tree_walk.py:372`. The geometry tests assert stop and only the first target's price; none asserts the full named/distinct target list or the obstacles forwarded at `tree_walk.py:548`.

A focused raw-fixture probe found 500 open zones and a priced Plan with two targets and one obstacle. Clearing only that in-memory Walk's zones before rebuilding left the entire stop/target/obstacle geometry identical. Thus the current full-walk pricing assertions do not indirectly establish the memory handoff. This is a missing explicit Task1 proof obligation, not a discovered runtime algorithm defect.

Add a small literal raw tape with hand-derived open/cleared vector zones and assert the resulting Walk tuples and memory evidence. Assert the complete expected named distinct targets and obstacles for the existing long/short raw-map geometry cases, including a coincident-price merge. Keep the expected values source/hand-derived. This closes the required consumer-binding checks without changing source behavior.

### Minor — M1: Raw trace and several explicitly requested test cases are incomplete

`tests/tree_replay/test_tree_walk.py:68`, `:71`, `:97`, `:108`, `:123`, `:166`, `:350`; requirements: `.superpowers/sdd/2026-09-10-tree-walk-reader/task-1-brief.md:24`, `:34`, `:48`, `:51`.

- `read_report` and `read_tv_csv` raise without recording their raw artifact reads. The successful full-walk test checks selected call counts and news adjacency, but never the full original ordered fetch/clock trace.
- DATA exception coverage supplies an absent 15m frame, but no raw 4h exception after a successful 15m read. The trap table omits blue-at-low and violet-at-high committed-side cases. The FirstVector prior-break test checks the immediately preceding close, but not the inclusion/exclusion boundary of the six-close window.

Record both artifact attempts before raising; add a literal successful-call trace and the named boundary cases. These are localized test completeness issues, not evidence that the runtime currently orders or classifies them incorrectly. In particular, **do not add a duplicate cloud-equality test merely because of its name**: the existing `ordinary` case at line 350 has a green PVSRA vector with close and upper cloud exactly 128, and already checks equality refusal.

## Verification reviewed

- Read the brief before the report/diff; reviewed the full diff in paged passes after the initial tool output was truncated. Used the requested task-reviewer template. Read AGENTS.md, exchange README/protocol, and inspected the Codex inbox. Startup `git status --short` and `git diff --stat` showed the existing dirty feature checkout; Task1 additions are represented by the supplied complete untracked-file diff.
- Named risk **unapproved source transformation/package drift**: a read-only `python -B -` AST/difflib probe reconstructed the five additions from the diff, compared them with the frozen files, compared the six complete methods and ordered core nodes with the retained original, and checked hashes. PASS. Original checkout HEAD ref is `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`; the LF-normalized tree blob is `fdb439a39bbd35230e421c0319c6be0e2fbfbc1d` (retained Windows file has CRLF). Original source was read/parsed only, never imported or executed.
- Named risk **raw-port substitution hides artifact/clock effects**: inspected the unchanged BasisOperation delegation and OptionsWallReader raw-read boundaries. Actual delegation is present; the test-side artifact trace gap is M1.
- Named risks **memory assertions are insensitive** and **cloud-equality coverage may be absent**: one `python -B -` probe loaded fixture definitions with `runpy.run_path('tests/tree_replay/test_tree_walk.py')`, without invoking test functions. Constructed the actual reader, checked no constructor IO, built the raw full Walk/Plan, cleared only the local Walk's zones and compared a second Plan; also checked the existing flat128 case against actual PVSRA/cloud and FirstVector. PASS with the observations reported in I1/M1. Read the unchanged vector-zone/PVSRA/cloud helpers only to resolve these named risks. No runtime/test file was edited.
- Reported, **not rerun**: normal missing-module RED 38 failures; current Task1 71 cases; planned combined command 250 passed in 5.92s, exit 0, reported pristine (`.superpowers/sdd/2026-09-10-tree-walk-reader/task-1-report.md:6`). The complete planned command is recorded there. No reported suite was rerun or regenerated. Historical RED timing and terminal transcript remain implementer evidence, not an independently witnessed run.
- Frozen SHA256 values: core `17e6dfd69ead1c19ad1f60cf33d3b651a266873a188d68d697142511b10cc8d9`; signals `909b66e3961f1ca298fab030c9af5479fbe91e303aa09092f6fb3fbc950cc22a`; reader `c7ef95f30c7d83b6f98d59d767afd229a070cde1b295b989196f28283518d117`; tests `2575f6ece8a59c8ea61e4afc657e8dcb2a2c4ce1ec1291bd8519a125e4d0ed89`; usage `ad001113da8e16b3adf07a1d65d551e8ceef825de702ec8ff06877727ef92c55`.

Open questions: None requiring a domain decision. Task2's full dependency audits/mutation proof and component final acceptance are outside this Task1 verdict and remain unverified here.

Recommended next action: Close I1 and the named M1 omissions in Task1 tests, report focused verification and updated hashes, then request scoped re-review. Preserve the runtime's audited source behavior. This review grants no full-replay, data, economic-label, model or live-action acceptance.

## Scoped re-review — Task1 fix round 1

Reviewed at: 2026-09-10 19:30:47 UTC
Scope: Original I1/M1 and new breakage in the fix only. This addendum supersedes the original NEEDS FIXES verdict for those findings; it does not repeat or expand the whole Task1 review.

**Spec compliance: PASS for the scoped fix. I1 ADDRESSED; M1 ADDRESSED.**
**Task quality: APPROVED for the scoped fix. No new blocking code/test defect found.**

- **I1 — ADDRESSED.** `tests/tree_replay/test_tree_walk.py:556` supplies literal OHLCV with separate open/cleared vector zones. `:573` asserts the actual zone rows and the full Walk's exact midpoint/kind/touch handoff, memory fact, observed-empty missing count, and distinct EQH/EQL annotation. `:389` asserts complete long/short named targets and Plan obstacles, including coincident-price merges, and the separate geometry consumer's complete targets. `:381` normalizes only order inside each merged name; rung order, price, membership and duplicate multiplicity remain checked. This closes the original I1 gap without relying on the insensitive full-fixture stop assertion.
- **M1 — ADDRESSED.** Artifact attempts are now recorded before raising (`tests/tree_replay/test_tree_walk.py:70`, `:74`) and checked at `:670`. The literal house/strict full-call trace and constructor silence are checked at `:634`; the raw 4h exception after successful 15m at `:110`; blue-at-low/violet-at-high at `:142` and `:144`; both sides of the sixth/seventh preceding-close boundary at `:604` and `:630`. The existing cloud-equality case is preserved.
- **Sensitivity/code-quality check:** `tests/tree_replay/test_tree_walk.py:677` compiles only the local candidate class into a copied namespace, without editing files or the imported module. Eleven mutations at `:689` use the same literal assertion helpers. Candidate construction happens before the expected `AssertionError` block (`:718`), and window mutations keep the price/cloud slices aligned (`:708`), so syntax/setup failures and pandas alignment exceptions are not accepted as detection. Scope remains focused on I1/M1.

### New non-blocking evidence issue

`.superpowers/sdd/2026-09-10-tree-walk-reader/task-1-fix-diff.md:57` and subsequent hunks contain 283 Unicode replacement characters in Hebrew strings; the actual test file contains none. This is review-package encoding damage, not damaged assertions. To resolve this named risk, I read the affected new assertions directly from the hashed test file and verified all six fix hunks against the original packaged baseline and current file, isolating the non-ASCII packaging damage; there are no changes outside those hunks. Prefer UTF-8-preserving diff generation for subsequent packages. This does not reopen I1/M1.

### Verification limits and snapshot

- Read `task-1-fix-report.md` and the complete `task-1-fix-diff.md`. Ran read-only AST/hash/hunk-consistency checks only; **no tests or suites rerun**.
- Reported focused result retained as implementer evidence: **95 passed in 7.25s, exit 0**, terminal `83c133`; 84 ordinary cases plus 11 mutation cases. The main combined run `89068` was reported running and is not claimed passed by this review.
- Current test SHA256 independently matches `283ecc81227dadd2ae1d52769785b10e8877851abb8128874584467a65ef4dab`. All three runtime files and the usage document independently match the original review hashes above.
- Only this review addendum was written, using apply_patch. No nested agents, runtime/test edits, commits, source execution, data or live actions.

Recommended next action: Controller may close I1/M1 and continue its existing combined-run/Task2/component acceptance workflow. No additional Task1 runtime change is requested by this scoped re-review.
