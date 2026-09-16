# Agent Exchange Review

Reviewer: Codex independent whole-component reviewer; no nested subagents.
Request: agent-exchange/inbox/codex/2026-09-10T195700Z-tree-binding-final-review.md
Target request: agent-exchange/inbox/codex/2026-09-10T195700Z-tree-binding-final-review.md
Created at: 2026-09-10 19:59:00 UTC
Status: REVIEW_READY_FOR_CODEX
Base/head: c1b6071633c55376c64f0a98ece843706f420f49; seven complete uncommitted additions across both tasks.

Spec verdict: PASS for the whole tree-revalidation-binding component.
Quality verdict: APPROVED.
Ready for component acceptance: YES.

## Strengths and cross-task evidence

- The runtime closes the intended decision boundary with actual calculations. `trading_system/tree_replay/_vendor/matrix_reader.py:10` retains the original fetch, correction rendering and complete-frame calculation; `:15` preserves requested timeframe order. `trading_system/tree_replay/tree_revalidation.py:11` constructs both readers on the raw source and Revalidation on the facade. Thus the tracker higher-bias consumer reaches the real matrix while pending tree checks reach the real TreeReader, rather than provider-final answers.
- The facade is narrow and inert. Its constructor, actual delegates and eight explicit raw forwarders match the contract (`tree_revalidation.py:11`, `:17`, `:23`, `:29`). The inherited BasisOperation retains fetch/UTC forwarding and its lazy splice clock (`_vendor/basis_operation.py:9`, `:14`, `:35`). `tree_revalidation.py:50` returns the supplied writer context manager unchanged. There is no dynamic forwarding, frozen decision clock, source-checkout lookup, implicit loader or new trading policy.
- Original result precedence survives composition. `trading_system/tree_replay/_vendor/revalidation.py:113` runs still_valid before age, and `:92` checks opposing direction before a later tree stop. The clean-tree result combines with the prior verified flag. `tree_revalidation.py:20` uses the original house default without deriving a variant from pending metadata. The binding does not invoke either Plan builder or convert the three-valued result into a fill or label.
- Task2 proves the exact Task1 implementation. `trading_system/tree_spec/tree_revalidation_source.py:12` independently specifies source imports/signatures and `:28` fixes the complete facade contract. The projection at `:67` retains both full ordered source functions with exact-count substitutions, including the complete TFView-to-read_frame substitution. Candidate comparison at `:132` includes imports, inheritance, signatures and executable order; only module/class docstrings are normalized for the facade.
- The substituted numerical implementation is covered transitively, rather than trusted merely because its name matches. `trading_system/tree_spec/admission_source.py:26` includes LOOKBACK, tools, TFView and read_tf; `:261` projects the original complete return as read_frame. `tree_walk_source.py:186` invokes the actual eight dependency auditors. The new parent invokes that actual graph and propagates blockers, false/empty reports and known input/StopIteration failures (`tree_revalidation_source.py:144`). Both readiness flags remain false (`:109`). Independent dependency probes below confirmed this cross-task closure.
- The runtime tests use raw tapes, literal expectations and adversarial final-provider methods (`tests/tree_replay/test_tree_revalidation.py:24`, `:32`, `:136`, `:149`). They cover history-sensitive ATR, correction/error propagation, matching/opposing decisions, the two-hour boundary, stopped paths, earlier vetoes, unavailable evidence, house default, shape/deep readers and ordered shadow effects. The source tests distinguish isolated local mutation checks from actual inherited-graph checks (`tests/tree_spec/test_tree_revalidation_source.py:31`, `:40`, `:176`), and cover the explicit-root CLI and guarded imports (`:187`, `:203`).
- `tools/check_tree_revalidation_source_parity.py:7` supports an unrelated cwd; `:15` requires an explicit root and returns JSON with 0/2 verification exits. Usage preserves the three-valued result and explicitly limits the component to raw-port integration (`docs/architecture/TREE-REVALIDATION-BINDING-USAGE.md:26`, `:48`). Its pending-acceptance wording is explicitly explained in final-report.md; controller bookkeeping follows this final gate.

## Findings

Critical: none.
Important: none.
Minor: none.

No findings are deferred, parked or waived. No problematic plan deviation was found. The intentionally excluded causal-provider/caller/lifecycle and economic/model work is outside this component's contract, not a deferred defect in these additions.

## Independent named-risk checks

1. **A whole-TFView substitution might escape numerical dependency proof.** Read the retained original matrix read_tf/read_symbol as text, the admission read_frame projection, the actual admission_matrix implementation and the tree auditor's dependency dispatch. Then ran an in-memory read interception replacing `reads=[fn(df) for fn in TOOLS.values()]` with `reads=[]` only in `_vendor/admission_matrix.py`. Both new binding projections still matched, but the actual parent graph returned BLOCKED with `DEPENDENCY:tree_walk:DEPENDENCY:admission:VENDOR_AST_MISMATCH:trading_system/tree_replay/_vendor/admission_matrix.py` (also propagated through revalidation). Both readiness flags stayed false. PASS.
2. **Inherited broker-shape time could change without changing the facade.** In the same guarded audit process, separately intercepted `_vendor/basis_operation.py` and replaced `pd.Timestamp(self.source.now_utc())` with a fixed timestamp. Both new projections again matched, while the actual graph returned BLOCKED with `DEPENDENCY:tree_walk:DEPENDENCY:levelmap_operation:VENDOR_AST_MISMATCH:basis_operation`. Both readiness flags stayed false. PASS. The audit process installed a meta-path guard rejecting chartdesk, floor and trading_system.tree_replay imports and asserted none were loaded; only AST/source text was inspected.
3. **A shared provider might inadvertently freeze the age clock around shadow IO.** Ran a separate raw-fixture probe with actual TreeRevalidation, matrix, tree and checks. The provider's now_epoch advanced by 0.25 seconds per call; the pending age began at 7199.999 seconds. Explicit `now=NOW.timestamp()` made seven shadow epoch reads and skipped the tree; omitted now made eight epoch reads, crossed the two-hour boundary and called the actual tree immediately after the final epoch read. Both retained valid/verified results. PASS. No finished reader result or still_valid implementation was patched; no retained-original modules were imported.

The two audit mutations used a PowerShell single-quoted here-string piped to `python -B -`, `unittest.mock.patch.object(Path, 'read_text', ...)`, and `audit_tree_revalidation_source(Path('C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149'))`. Assertions required BLOCKED, both unchanged new projections, the named inherited blocker, and false readiness. Terminal 28911/chunks 794fb6 and 7dd999: exit 0. An initial invocation's terminal output was not retained and is not used as evidence; this recorded invocation supplies both results. No files were patched by these probes.

The advancing-clock probe also used `python -B -`, importing only the existing raw fixture Inputs/pending/NOW/SYMBOL and the local TreeRevalidation. It overrode only the raw provider's now_epoch, asserted distinct timestamps, seven versus eight calls and absence/presence of the first tree fetch. Chunk 5300a2: exit 0, PASS. These were focused dependency/clock probes, not reruns of the reported suites.

## Verification reviewed and artifact integrity

Read AGENTS.md, exchange README/protocol, the request, requesting-code-review/SKILL.md and its code-reviewer.md rubric, the full component plan/contract, final-report.md, progress.md and all seven additions in final-review.diff. Also read both task reports/reviews and acceptance statuses. Inspected startup git status/diff summary and confirmed HEAD; the tracked-only diff cannot represent these untracked additions. Review covered both tasks together, not only the most recent audit addition.

Reported verification, reviewed without rerunning:

- `python -B -m pytest tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_revalidation.py tests/tree_replay/test_admission_frames.py -q --tb=short -p no:cacheprovider` — 240 passed in 19.87s, exit 0 (91972/eaa544).
- `python -B -m pytest tests/tree_spec/test_tree_revalidation_source.py -q --tb=short -p no:cacheprovider` — 51 passed in 32.46s, exit 0 (72424/4daa34).
- `python -B -m pytest tests/tree_replay/test_tree_revalidation.py tests/tree_spec/test_tree_revalidation_source.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_revalidation.py -q --tb=short -p no:cacheprovider` — 250 passed in 49.26s, exit 0 (26887/f4139c).
- `python -B tools/check_tree_revalidation_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149` — controller reports post-Task2-review VERIFIED, exit 0, no blockers and both readiness flags false.

Counts overlap and are not summed. These suite/clean-CLI results are implementation/controller evidence, not claimed independent reruns. Initial missing-module/auditor RED and terminal combined GREEN are distinguished in the reports.

Independent `Get-FileHash -Algorithm SHA256` checks before and after probes matched all seven hashes in final-review.diff; final check bb795a exited 0:

| File | SHA256 |
| --- | --- |
| trading_system/tree_replay/_vendor/matrix_reader.py | 73397F6B94DB2A24BEE76DD0D02788DB701685D9C7D6481571232AFF430948D0 |
| trading_system/tree_replay/tree_revalidation.py | 423C8A983EE77A9C0962EB3E65C64678FA6172A9E8E2C2ECB3053107F7FD808E |
| tests/tree_replay/test_tree_revalidation.py | 1CD640CF36923C89B07A41EEDEB59BE0712970BA7A2F5CF2995A117A59DCF9F8 |
| docs/architecture/TREE-REVALIDATION-BINDING-USAGE.md | 2E99DC2E256761CD19A74983B5CE5ABF93333BA77FDEEA5E3F2212C2D61C38B9 |
| trading_system/tree_spec/tree_revalidation_source.py | 37AECFB39FFA01F7FC7035CA0D330DDC6914DFD2E3F28FD419A3E297DF07876E |
| tools/check_tree_revalidation_source_parity.py | EC829803902285CF7039F48FEF14CFD1137DC8D83EF30D4D947AA275656AD4CA |
| tests/tree_spec/test_tree_revalidation_source.py | 04988816BA3025929F0FADB82C0A78F7ECDE02EB03FAE80D6D515B2C04CD9FBB |

## Assessment and next action

Ready to merge/accept within this component's scope: YES. The runtime composition preserves source behavior, and its independent audit covers both new adapters plus their actual inherited numerical, clock and revalidation dependencies. Tests and targeted probes substantiate the critical cross-task boundaries; no revision is requested.

Open questions: none for this review. Recommend controller component acceptance and the already planned accepted-scope documentation update. This verdict does not certify historical causal feeds, original market-watch lifecycle/arbitration, full replay, fills, economics, datasets, models or deployment. No commit/push or external action is authorized by this review. Only this matching review file was written; no runtime/test changes or nested agents.
