# Task1 independent spec and quality review

Spec compliance: PASS for Task1.
Task quality: APPROVED.

Reviewer: Codex independent Task1 reviewer; no nested subagents.
Request: agent-exchange/inbox/codex/2026-09-10T195000Z-tree-revalidation-binding-task-review.md
Target request: agent-exchange/inbox/codex/2026-09-10T195000Z-tree-revalidation-binding-task-review.md
Created at: 2026-09-10 19:51:11 UTC
Status: REVIEW_READY_FOR_CODEX
Base/head: c1b6071633c55376c64f0a98ece843706f420f49, four uncommitted full additions in the supplied package.

## Spec compliance

- All four required additions are present. MatrixReader preserves ordered requests, direct correction rendering and full-frame delegation to the existing numerical implementation (`trading_system/tree_replay/_vendor/matrix_reader.py:10`, `:15`). It adds no correction fallback, history trimming or exception suppression.
- The facade constructs MatrixReader and TreeReader on the same raw source and Revalidation on itself (`trading_system/tree_replay/tree_revalidation.py:11`). Actual tree/matrix delegates, both check entrypoints and all eight explicit raw forwarders match the contract (`:17`, `:20`, `:23`, `:26`, `:29`). The writer context manager is returned directly (`:50`). No provider-final dispatch, clock cache, dynamic forwarding, Plan construction or runtime source lookup was added.
- The tests exercise raw calculations and actual consumers: inert construction/DATA stop (`tests/tree_replay/test_tree_revalidation.py:92`), ordered matrix requests and directional reads (`:102`), propagated errors (`:120`), visible correction (`:130`), a hand-derived history-sensitive ATR (`:136`), and matching/opposing pending checks with unchanged input and ordered shadow effects (`:149`). The remaining tests cover the exact age boundary, stopped paths, opposition precedence, earlier veto, unavailable evidence, operation-clock dispatch, source shape, deep fallback and house default.
- Usage accurately retains the three-valued result and limits this component to raw-port integration (`docs/architecture/TREE-REVALIDATION-BINDING-USAGE.md:26`, `:48`). Task2 audit and historical-feed certification are not claimed.

## Strengths

- The new production surface is only 67 lines across two focused modules; numerical rules and revalidation policy remain in their existing owners (`matrix_reader.py:13`, `tree_revalidation.py:26`).
- The test provider makes final-verdict methods fail if consumed (`tests/tree_replay/test_tree_revalidation.py:32`), while the successful integrated cases require genuine calculated results. Expected ATR is independently expressed rather than derived from the implementation (`:136`).
- Shadow IO uses an in-memory context manager with explicit write/close evidence (`tests/tree_replay/test_tree_revalidation.py:64`); facade construction and forwarding introduce no external loader or writer defaults (`tree_revalidation.py:11`, `:47`).

## Findings

Critical: none.
Important: none.
Minor: none.

## Named-risk dependency checks

- **Altered result precedence or operation clocks:** inspected the existing `Revalidation` constructor, `_tree_agrees`, `revalidate_pending`, shadow writer and relevant raw consumers (`trading_system/tree_replay/_vendor/revalidation.py:86`, `:92`, `:113`, `:136`, `:152`), plus `BasisOperation` forwarding and lazy splice clock (`_vendor/basis_operation.py:6`, `:9`, `:35`). The new delegates retain still-valid-before-age, opposition-before-stop, independent clock calls and unavailable evidence flags.
- **Wrong numerical projection or request constants:** inspected `admission_matrix.LOOKBACK`, ordered tools, TFView and `read_frame` (`_vendor/admission_matrix.py:11`, `:111`, `:116`, `:146`). The new wrapper passes the original frame and rendered note through unchanged.
- **Fixture secretly supplying final decisions or live IO:** inspected only the reused raw fixture definitions in `tests/tree_replay/test_tree_walk.py:26`, `:30`, `:38`, `:79`, `:275`. They generate/copy OHLCV, corrections and raw artifacts; they do not compute expected binding results or supply completed Walks. The future low-impact calendar row is explicit at `:43`.
- **Wrong tree source or variant:** inspected TreeReader construction and its walk signature (`_vendor/tree_walk.py:17`, `:70`); the facade uses the raw source and original default house. Prerequisite acceptance is explicitly recorded in `agent-exchange/status/2026-09-10T193848Z-codex-tree-walk.md` as ACCEPTED_BY_CODEX.

## Verification reviewed

- Read the brief before the report and complete supplied 479-line package, then the named dependency checks above. No changed file was separately reread for code review, no original repository was imported/executed, no live IO was performed, and no test suite was rerun.
- Reported command: `python -B -m pytest tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_revalidation.py tests/tree_replay/test_admission_frames.py -q --tb=short -p no:cacheprovider`. Implementer reports **240 passed in 19.87s, exit 0**, including 27 new cases, with pristine output. This is reviewed implementation evidence, not an independent execution claim. Initial missing-module RED and intermediate fixture corrections are distinguished in the report.
- Independent `Get-FileHash ... -Algorithm SHA256` check: **PASS**, all four files match the supplied package hashes: matrix `73397F6B94DB2A24BEE76DD0D02788DB701685D9C7D6481571232AFF430948D0`; facade `423C8A983EE77A9C0962EB3E65C64678FA6172A9E8E2C2ECB3053107F7FD808E`; tests `1CD640CF36923C89B07A41EEDEB59BE0712970BA7A2F5CF2995A117A59DCF9F8`; usage `2E99DC2E256761CD19A74983B5CE5ABF93333BA77FDEEA5E3F2212C2D61C38B9`.
- Package-generation LF/CRLF warnings are Git formatting notices, not pytest warnings. The reviewer timestamp command `Get-Date -AsUTC` was unsupported in this PowerShell version; `[DateTime]::UtcNow.ToString(...)` succeeded. Neither command executed application code.

## Open questions and next action

Cannot verify from these four additions alone: complete pinned-source AST equivalence and inherited graph integrity, or the absence of unrelated workspace changes. The former is explicitly Task2's source-proof work; the latter remains controller intake responsibility. This review does not approve Task2 or the whole component.

Recommended next action: record Task1 acceptance and complete the separately prepared Task2 source audit and independent review. No Task1 revision requested.
