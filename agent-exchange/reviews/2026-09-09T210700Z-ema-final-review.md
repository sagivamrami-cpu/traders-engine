# Agent Exchange Review

Reviewer: Codex independent final reviewer; no nested agents

Target request: agent-exchange/inbox/codex/2026-09-09T210700Z-ema-final-review.md

Request: agent-exchange/inbox/codex/2026-09-09T210700Z-ema-final-review.md

Created at: 2026-09-09T21:08:52Z

Status: REVIEW_READY_FOR_CODEX

Verdict:

- Final combined spec compliance: **PASS**.
- Final combined code quality: **PASS / Approved**.
- Task 1 M1: **CLOSED**, independently checked against both added tests and discriminating candidate-only mutations.
- Ready for controller component acceptance: **Yes**. This is not merge/full-master acceptance, historical feed certification, replay readiness, training readiness or production approval.

Findings:

- Critical: none.
- Important: none.
- Minor: none open in this six-file component. The prior M1 coverage note is resolved.

Strengths and combined fidelity assessment:

- `trading_system/tree_replay/_vendor/ema_windows.py:8` preserves the five exact symbol mappings, six EMA lengths, original constants and complete Window/EmaState behavior. I read the complete pinned `chartdesk/emawin.py` as text and the exact `basis.py` mapping. The imported seeded recursion is the real local `indicators.ema`, not a supplied finished state or a substitute EMA calculation.
- `trading_system/tree_replay/_vendor/ema_windows.py:226` retains per-length convergence, strict pre-live prefix selection, splice-only keep-last deduplication/sorting, live close/window ATR, and the original terminal-NaN and slope handling. For short live input, slope ATR can include deep rows; the independent numerical probe at `tests/tree_replay/test_ema_windows.py:239` distinguishes that divisor from live ATR. Raw floating comparison behavior remains intact.
- `trading_system/tree_replay/_vendor/ema_windows.py:266` and `:281` implement the six specified adaptations and preserve their exception boundaries. Fetch remains outside the deep-IO catch, real CSV/time parsing remains inside it, and calculation remains after it. Source defaults/truthiness, logical filename guard, correction annotation, repeated timeframe reads and per-read stack omissions remain unchanged. No default IO provider or native filesystem/network access was added to the reader.
- `trading_system/tree_spec/ema_windows_source.py:36` builds the complete ordered candidate projection: fixed imports, original mapping, all pure definitions and EmaReader with constructor/read/read_stack in order. `:56` independently fixes the source commit and both blobs and checks repository identity and the baseline. Full candidate comparison retains annotations, properties, rendering, numerical bodies and catches; only the initial module docstring is excluded.
- Named combined risk: a correct reader projection could otherwise conceal a changed numerical dependency. `trading_system/tree_spec/ema_windows_source.py:99` calls the actual strict EMA audit using the same chart-desk root. `tools/check_levelmap_source_parity.py:249` independently pins the indicators and TR blobs and compares their ordered local projections through `:238`. I inspected the actual seeded recursion and package initializers. Independent probes confirmed that reordering either actual dependency fails overall verification even while `checked_projections` remains `['ema_windows']`.
- Named transformation risk: omitted or duplicated replacements, reordered source symbols, or extra candidate statements could produce a false pass. `trading_system/tree_spec/tracker_admission_source.py:150` enforces exactly one match per replacement, and `:167` compares the selected sequence, including duplicates, against the required sequence. The reader auditor compares the complete candidate body. Its Git/JSON helpers are read-only and reject duplicate JSON keys. An independent fresh-process import guard confirmed successful combined auditing without importing chartdesk, floor or any tree_replay module.
- `docs/architecture/EMA-DEEP-READER-USAGE.md:39` accurately describes the live/deep distinction and source three-bar slope. Its causal availability, raw input, GC/spot seam and readiness limitations match the implementation. Runtime construction is not represented as running the audit or certifying the inputs.

M1 closure:

- `tests/tree_replay/test_ema_windows.py:308` uses signed slopes `[1, -9, 3, -7]`; sorted magnitudes are `[1, 3, 7, 9]`, so the asserted median is 5. This distinguishes averaging the two middle magnitudes from either middle element or a signed median.
- `tests/tree_replay/test_ema_windows.py:317` drives the actual reader with 1,600 descending bars. It asserts all-window convergence, close 401, EMA800 800.5, strict/loose down labels, all slow windows lost, negative distances/slopes, agreement -1, full coverage and strength 1.5.
- Both tests passed independently. In-memory replacement of the even-median expression by `vals[mid]` caused the first test to fail. Replacing only `if all((w.distance < 0 for w in need)):` with `if False:` caused the generated descending test to fail. Each expected AssertionError was required by the outer probe, which exited 0. Only local candidate code was executed; retained source was never compiled or executed.
- Programmatic package comparison confirmed that the M1 supplement adds exactly these two functions and leaves every earlier runtime-test AST node unchanged. All six current file texts match their supplied diff packages, using task-1-m1-diff.md only for the runtime-test replacement. Runtime and the other four files are unchanged from the original packages.

Verification reviewed:

1. Startup/scope: read AGENTS.md, exchange README/protocol, inspected the Codex inbox, read the final request, both exact task briefs, all applicable diff packages, contract, implementation plan, implementation report, progress ledger, task review and its original request. Read the actual task-intake status `agent-exchange/status/2026-09-09T210700Z-ema-task-intake.md`; it accepts the tasks but explicitly leaves final component acceptance pending. Used the requested requesting-code-review/code-reviewer guidance directly, without dispatching agents.
2. Checkout: `git status --short`, `git diff --stat`, `git diff -- AGENTS.md README.md`, and `git rev-parse HEAD` completed. HEAD is `c1b6071633c55376c64f0a98ece843706f420f49`. The six files are additive uncommitted work amid unrelated pre-existing changes. Their full review diffs are the supplied packages, not the empty tracked diff for those additions. Output portions truncated by the tooling were recovered with smaller targeted reads. A guessed status filename was absent; discovery identified the actual task-intake path above, which was read. This was a lookup error, not a verification failure.
3. Independent focused runtime/audit command: **PASS, 8 passed in 0.84s, exit 0**, no reported warnings:

```text
python -B -m pytest tests/tree_replay/test_ema_windows.py::test_even_slope_strength_averages_two_unequal_middle_magnitudes tests/tree_replay/test_ema_windows.py::test_generated_descending_tape_has_strict_downtrend_and_negative_slope tests/tree_replay/test_ema_windows.py::test_actual_csv_deep_prefix_extends_only_unconverged_windows_and_live_endpoint_wins tests/tree_replay/test_ema_windows.py::test_short_live_keeps_window_atr_live_but_slope_atr_includes_deep_span tests/tree_replay/test_ema_windows.py::test_parsed_but_nonnumeric_deep_raises_outside_optional_io_catch tests/tree_replay/test_ema_windows.py::test_fetch_failure_propagates_but_stack_omits_only_failed_timeframe_and_repeats_reads tests/tree_spec/test_ema_windows_source.py::test_complete_reader_and_real_seeded_ema_verify_without_readiness tests/tree_spec/test_ema_windows_source.py::test_actual_indicator_dependency_drift_blocks_verification -q --tb=short -p no:cacheprovider
```

4. Independent package/M1 probe: `@'<inline script>'@ | python -B -`, **PASS, exit 0**. Parsed the added lines of task-1-diff.md, task-2-diff.md and task-1-m1-diff.md; required exact normalized-text equality with all six files; compared old test AST with the new AST excluding its last two functions; then executed the two candidate-only substitutions described under M1 against the actual new test functions. Output: six `PACKAGE_MATCH`, `M1_DELTA exactly two added test functions; all prior test AST unchanged`, and `MUTANT_KILLED` for both `upper_median` and `disabled_strict_down`. No file writes.
5. Independent dependency/import probe: separate `@'<inline script>'@ | python -B -`, **PASS, exit 0**. Installed a MetaPath finder rejecting prefixes `chartdesk`, `floor`, `trading_system.tree_replay` before importing the auditor. Called `audit_ema_windows_source` with explicit retained parent `C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`. Clean result:

```json
{"status":"VERIFIED","source_subset_verified":true,"blockers":[],"checked_projections":["ema_windows"],"dependencies":{"ema":{"source_subset_verified":true,"blockers":[]}},"source_commits":{"chart-desk":"68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"},"ready_for_replay":false,"ready_for_training":false}
```

   In each of two independent read-only monkeypatch contexts, intercepted only the selected local dependency's `Path.read_text`, parsed its AST and swapped its first two top-level FunctionDef nodes. The reader projection still matched, but the overall audit blocked with exactly:

```text
DEPENDENCY:ema:STRICT_EMA_VENDOR_AST_MISMATCH:trading_system/tree_replay/_vendor/indicators.py
DEPENDENCY:ema:STRICT_EMA_VENDOR_AST_MISMATCH:trading_system/tree_replay/_vendor/tr.py
```

   After both probes, no forbidden-prefix modules were present in sys.modules. No source/runtime execution by this audit probe and no file writes.
6. Main evidence, reviewed rather than duplicated: current runtime/audit **103 passed in 7.37s, exit 0** after M1; prior combined **255 passed in 14.13s, exit 0** before the two test additions, with unchanged runtime. The 255 command was:

```text
python -B -m pytest tests/tree_replay/test_ema_windows.py tests/tree_spec/test_ema_windows_source.py tests/tree_replay/test_ema.py tests/tree_replay/test_stretch.py tests/tree_spec/test_stretch_source.py -q --tb=short -p no:cacheprovider
```

   The implementation report also records head-only splice and keep-first candidate mutations caught by numerical tests, plus its upper-median mutation. These historical runs were not independently reproduced here except for the new independent median probe above. Counts overlap; they are not added together. The task review's static assessment and hashes were cross-checked, not treated as a substitute for this final inspection.
7. `Get-FileHash <six scoped paths> -Algorithm SHA256` before and after focused verification: **PASS**, identical hashes and matching report/package evidence:

| File | SHA256 |
| --- | --- |
| trading_system/tree_replay/_vendor/ema_windows.py | B632AD21C88DF94CD2D92732273E510A662F50DAC7D523CEA5EF25F5F321A774 |
| tests/tree_replay/test_ema_windows.py | A7330C4F4D5BEB6FF689519C10BBFA5C28CD4E56D3B472CE86239578A35EBE49 |
| docs/architecture/EMA-DEEP-READER-USAGE.md | C7A0931657E12543851C5A332E05C3CB7AD8F8F8B4A9E0E32E6B57F5B0910257 |
| trading_system/tree_spec/ema_windows_source.py | 2EC14738974D42AE1FDD64B2A9AD0B0E1D9C2507552D70CB6F2CAED692060B01 |
| tools/check_ema_windows_source_parity.py | 29B56167AF1AF45A1774A1E2185364F69DB4A0F19FC4DB81C5C9BA085CC67D93 |
| tests/tree_spec/test_ema_windows_source.py | A32A37545DE2635E218AD6EEBBC16702C2D2D7ED087A57A70442998367836D22 |

Open questions / verification limits:

- No blocking implementation questions or unverified runtime contract requirement identified. Historical RED-before-implementation ordering and full historical execution transcripts are not independently established; the implementation report supplies summarized evidence.
- CLI unrelated-CWD/exit-2 behavior and the complete mutation matrix were inspected in the supplied audit tests and prior evidence, not rerun in this final seat. No full-repository, broad tree or duplicate combined suite was run.
- Raw supplied frames/bytes, current-bar and publication policies, session calendars, deep seam provenance and causal provider tracing remain future binding obligations. The guarded VERIFIED result certifies the specified source/dependency projection only. It does not establish complete historical-loop behavior or numerical feature suitability for training.
- Controller status/memory/tracker updates after this final review remain controller work. The disjoint revalidation contract/component was not reviewed here.

Recommended next action:

Record controller acceptance of this six-file component and M1 closure with the hashes and evidence above, then continue the separately scoped causal/revalidation work. No code revisions or further broad reruns are requested by this review.

Only this named review artifact was written, via apply_patch. No nested agents, retained-source execution, live IO, market-data acquisition, labels/training, commits, cleanup or production approval. All independent verification commands reached terminal exit; no reviewer-owned tests remain running.
