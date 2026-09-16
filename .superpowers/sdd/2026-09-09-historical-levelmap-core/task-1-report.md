# Task 1 implementation report — complete level-map source graph

Target:
Codex controller

Sender:
Codex scoped Task 1 implementer

Created at:
2026-09-09T11:14:44Z

Request:
agent-exchange/inbox/codex/2026-09-09T110000Z-levelmap-source.md

Exact task contract:
.superpowers/sdd/2026-09-09-historical-levelmap-core/task-1-brief.md

Status:
IMPLEMENTED_AWAITING_CODEX_REVIEW

## Summary

Implemented the complete original level-map calculation graph with the specified
offline source and explicit clock injection. The new graph audit verifies the
entire ordered source projection and every required inherited dependency audit.
The controller's subsequent EMA trust/order finding is covered by independent
fixed source pins and strict ordered projections of the existing EMA vendors.

Final focused verification: **146 passed in 96.96s**, exit 0.
Final source audit: **PASS**, exit 0, no blockers, all four inherited audits
verified. Both replay and training readiness remain false.

This is Task 1 only. The causal frame builder, public historical-map adapter,
controller review and broad integration tests are not claimed by this report.

## Owned changes

1. trading_system/tree_replay/_vendor/levelmap_build.py
   Complete NamedLevel including __repr__, SESSION_OPEN_LEVELS, the two original
   helpers and build, preserving their source order and bodies except the exact
   specified source/decision-time injections and call rewrites.
2. trading_system/tree_replay/_vendor/map_sessions.py
   Complete SessionSpec, SESSIONS, _hm and psy_levels; specified imports only.
3. trading_system/tree_replay/_vendor/map_tr.py
   Two composition imports only: existing emas and existing weekly/monthly/range
   functions. No calculations duplicated.
4. tools/check_levelmap_source_parity.py
   Fixed commit/blobs/contracts, ordered whole-module AST comparisons, explicit
   transformation preconditions, dependency manifest seals, inherited audits and
   additional strict EMA dependency projections. Configurable read-only CLI.
5. configs/trees/levelmap-source-contracts.json
   Exact projection, adaptations, dependency tools, accepted manifest SHA256
   values and strict EMA source/import/symbol contracts; false readiness flags.
6. tests/tree_replay/test_levelmap_source.py
   Synthetic behavioral fixtures, real existing calculations, relocated audit
   mutation tests, source projection precondition checks and controller-named
   EMA trust/order regressions.
7. docs/architecture/LEVELMAP-SOURCE-USAGE.md
   Interfaces, source asymmetries, original omissions/exception behavior,
   audit guarantees and downstream responsibilities.

Additional authorized outputs:
- This report.
- agent-exchange/status/2026-09-09T110000Z-worker-levelmap-source.md.

No accepted dependency, old audit tool, parent implementation, tracked dirty
file, source checkout or inbox file was changed. Git status was inspected at
startup and self-review. Existing tracked AGENTS.md/README.md changes and the
large pre-existing untracked research slice were preserved. New parent frame
work appearing during the task was left alone.

## Source identities and text-only evidence

Source root:
C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk

Pinned commit:
68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9

New source projection blobs:
- chartdesk/levelmap.py: 01fc9fe098aa7a5991ce62c3a83e870e4f0d5a2e
- chartdesk/sessions.py: 2f44d322178feb14b0488abda51b40581db5b31f

Before adding independent strict EMA pins, ran this exact read-only Git command:

```powershell
git -C C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk rev-parse 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9:chartdesk/indicators.py 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9:chartdesk/tr.py
```

Exit 0; exact output:

```text
672f0428c3a81b86376d4f792ae40ecd174a2025
8297c712d20404880d4d8949e96efbf48613909c
```

Source was read as UTF-8 text and parsed into ASTs for projection/audit; source
modules were never imported, executed or downloaded. The graph's vendor files
were created via apply_patch from selected text, preserving original comments
within selected definitions and complete docstrings. New audit code independently
derives the expected AST; audit never executes source or vendor modules.

Canonical source blob hashing normalizes checkout CRLF through read_text to Git
LF. Dependency manifest seals hash UTF-8 json.dumps(sort_keys=True,
allow_nan=False), distinguishing false from 0 and fixing the complete accepted
configuration independently of any subsequently mutated manifest.

## Exact RED / GREEN record

Primary command (each full run below used this exact command):

```powershell
python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short
```

- Initial test harness run: 63 failed, 60 errors in 7.83s, exit 1.
  Every failure/error was the explicit missing-assigned-module assertion; 60
  assertions occurred during fixture setup. This was not accepted as the clean
  RED checkpoint.
- Corrected harness before production edits: **123 failed in 6.81s**, exit 1.
  All are expected missing-assigned-module assertion failures, with no setup
  errors. This is the Task 1 RED checkpoint.
- First implementation run: 5 failed, 118 passed in 87.72s, exit 1.
- Next run during fixture correction: 2 failed, 121 passed in 74.23s, exit 1.
- Initial GREEN: **123 passed in 78.21s**, exit 0.
- Additional boundary/structural characterization before controller's EMA
  follow-up: **139 passed in 82.18s**, exit 0. These additional existing-behavior
  checks do not claim their own pre-implementation RED.
- Final complete Task 1 suite after the EMA strengthening:
  **146 passed in 96.96s (0:01:36)**, exit 0.

Intermediate failures were test expectations/fixtures, not changed source
calculations: seeded EMA constant-100 output is 100.0000000000001; the complete
ordered map contains 31 ordinary levels plus 2 PSY, 4 EMA and 4 quarter levels;
the relocated source fixture originally omitted auction.py, which inherited
reversal auditing requires. Corrected tests use hand-derived numeric expectations
with floating tolerance where appropriate, the accurate family count and all
required source-text dependencies. No source formula was changed to fit tests.

Controller-named EMA regression command:

```powershell
python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short -k 'joint_indicators or tr_emas_after or strict_ema_projection'
```

- Before strict EMA implementation: **6 failed, 1 passed, 139 deselected in
  11.64s**, exit 1. The positive case was harmless initial module documentation.
- After strict EMA implementation: **7 passed, 139 deselected in 12.23s**,
  exit 0.

The coordinated indicators source/vendor/manifest mutation was already blocked
by the independent manifest seal. Its RED assertion specifically required the
additional fixed source-blob mismatch evidence; the other five REDs demonstrated
actual full-graph false positives from legacy set-based ordering checks.

## Controller-named dependency finding: disposition

The tests mutate relocated copies only. Trusted production pins and accepted old
tools are never monkeypatched.

1. Change indicators' EMA multiplier from 2/(length+1) to 1/(length+1) in both
   source and vendor, and update its manifest blob to match the modified source.
   The unchanged legacy EMA audit reports verified (demonstrated in the test).
   The new graph audit returns exit 2 with both DEPENDENCY_CONTRACT_MISMATCH:ema
   and STRICT_EMA_SOURCE_BLOB_MISMATCH:chartdesk/indicators.py.
2. Move TR_EMAS after emas/ema_cloud, retaining all selected nodes and imports.
   The unchanged legacy EMA audit again reports verified. The new graph audit
   returns exit 2 with STRICT_EMA_VENDOR_AST_MISMATCH. The mutated module is
   never imported, so the broken default argument is detected without execution.
3. Reorder imports, duplicate a pandas import, reorder indicators functions, or
   append a noninitial string statement. The new strict projection rejects all.
4. Change only an initial module docstring. Verification remains successful.

Strict EMA coverage is independently pinned in the new tool and manifest:
indicators imports plus _seeded_recursive/ema/stdev; tr imports plus
TR_EMAS/emas/ema_cloud, each in original order. Only an optional initial vendor
module docstring is ignored. Required range/pricing/EMA/correction audit calls
remain intact, including pricing's inherited reversal audit. All dependencies
are attempted even if another manifest/audit is blocked.

## Source audit results

```powershell
python tools/check_levelmap_source_parity.py
```

Final run: PASS, exit 0, blockers=[], subset_verified=true,
source_subset_verified=true, ready_for_replay=false, ready_for_training=false.
dependency_audits contains range, pricing, ema and correction, each with
source_subset_verified=true, no blockers and both readiness flags false.

The final run also executed strict whole-module EMA dependency comparisons.
No source/vendor execution occurred in the audit. CLI precedence tests prove
--source-root overrides TR_CHARTDESK_SOURCE_ROOT, and the environment overrides
the retained default. Missing source produces a blocked JSON report and exit 2.

Mutation coverage includes baseline missing/duplicate/wrong commit; source blob;
exact manifest files/symbols/order/imports/readiness/false-vs-zero; vendor
guards, clocks, signatures, class fields, omitted symbols, reordered imports,
composition, extra/rebound statements, missing/syntax-invalid modules; all
inherited calculation families and missing/invalid/changed dependency manifests
or missing dependency checker. Source transformation preconditions reject
unexpected signatures, clock assignment, helper calls, symbol/import set/order
and source-injection collisions.

## Behavioral coverage

- Literal daily fixture: 15 prior ranges 110–90, current O100/H115/L95/C110.
  Broker shape yields ADR/RD 115/95, from-open rails 110/90. Shape false removes
  ADR/RD while original other branches remain.
- Complete family order/prices/kinds, pivot and extra-EMA exclusions, duplicated
  Q-QUARTER names at distinct prices and nearest ordering.
- Daily fetch failure; warmup; yday/D2–D4; weekly/monthly/RW guards; omitted
  family and EMA diagnostics.
- None/none/replay/broker/native/splice correction sources; real accepted
  correction shape predicate, including exact 20-day and 7-day boundaries.
- Exact London/NY opening bars, summer/winter and mismatched DST weeks,
  inclusive starts/exclusive closes, weekends, UTC normalization, no nearest or
  previous-day substitution, splice pre-seam exclusion and seam equality.
- Forex/crypto PSY windows, planned end while forming, end exclusion, gaps of
  exactly 12h versus 13h, insufficient bars/resolution, absent window, 1h to
  actual 15m fallback, exception/coarse/empty-after-seam break semantics and
  clipping pre-seam extremes.
- EMA 400/1600 hourly and 100/400 four-hour requirements; real seeded values;
  CLOUD50's basis rather than band; original missing/fetch-error behavior.

Only the external fetch/correction interface is supplied by offline fixtures.
Range, EMA, PSY and quarter calculations are real, not stubbed outputs.
Synthetic forced broker flags are used explicitly to isolate original consumer
guards/edge paths; the source-identity matrix uses the real correction predicate.

## Self-review and limitations

Self-reviewed owned code and test changes against the exact task brief, source
text, complete-module audit, final verification output and controller amendment.
Used the TDD skill and its writing-good-tests reference before production edits,
and verification-before-completion guidance for the final evidence.

Whitespace: ran git diff --no-index --check -- NUL <file> for each of the seven
owned implementation/test/config/doc paths. Every command returned 1 for an
added file; output contained only LF-to-CRLF advisories, no whitespace-error
diagnostics. This is not described as seven zero-exit checks.

No unresolved Task 1 implementation concern was identified in self-review.
Independent controller review remains required; this is not self-acceptance.

Preserved limitations:
- The low-level graph assumes valid caller frames, binding and decision time.
  It neither certifies publication/history nor constructs causal frames.
- The injected shape predicate must share the graph's clock. None is not a valid
  caller clock; no new validation is inserted into the exact source projection.
- Original asymmetric correction gates, silent omissions and exception
  boundaries remain. missing is not a complete readiness/coverage report.
- PSY may be forming; an accepted empty-after-seam or coarse frame does not
  trigger fallback. Source behavior is retained and documented.
- The original quoted basis.Correction return annotation has no global live
  basis binding; consumers should not assume get_type_hints can resolve it.
- Accepted dependency manifest seals intentionally require review when a
  dependency's full contract changes.
- Full replay, real source/holiday provenance, producer admission/arbitration,
  simulation, economic labels, datasets and training are outside Task 1.

Decisions needed:
None for Task 1. GC versus OANDA source selection and later real-data gates
remain existing controller/human matters; no alias or permission was inferred.

Recommended next action:
Controller independently reviews these exact files, reruns focused/source audit,
and performs its causal-frame/public-map integration and broad tests.

No nested agents, commits, pushes, worktrees, cleanup, data downloads, live
source execution, real market data, training, alert changes or external messages.
