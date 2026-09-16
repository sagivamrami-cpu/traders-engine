# Tree Replay Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task; use test-driven-development and verification-before-completion. User authorized starting implementation in the current conversation. Do not request that same authorization again.

**Goal:** Preserve the supplied tree faithfully and implement a tested point-in-time input boundary without pretending the tree is already executable.

**Architecture:** An additive `trading_system.tree_spec` package extracts a version-specific evidence catalog from inert HTML. A separate snapshot module validates typed, timestamped observations against explicit pre-entry definitions. Neither component generates candidates, labels, model promotions or broker actions.

**Tech Stack:** Python standard library, existing pytest; no new runtime dependency.

**Spec:** `docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md` (full agreed design, roadmap A–J and domain acceptance requirements).

**Subsequent approved scope amendment:** Read
`agent-exchange/decisions/2026-09-08T180046Z-user-economic-target-and-baseline.md`
and the current master plan before phases B–J. A1–A3 below are historical completed
tasks; their HTML readiness blocker does not mean chart-desk has no executable tree.
Reuse the pinned existing producers and calculations. Initial economic management
is original stop/full TP1 without optional partials/scale/BE/trailing; movement
outcomes remain separate. Phase E's broader management cases below belong to
later research, not the first economic baseline. Do not re-request broad feature
definitions already implemented in the six repositories.

## Global Constraints

- No invented trading thresholds, feeds, outcomes or approvals.
- Preserve legacy engines, datasets and plans; do not silently change their semantics.
- Source inventory is not executable coverage; initial readiness must remain blocked.
- No future outcomes in pre-entry inputs; missing values are not false or zero.
- Local research implementation only; production boundaries in AGENTS.md remain in force.
- Run source extraction without executing HTML JavaScript.
- Keep the complete source, including graph scripts; do not claim graph semantics are parsed.
- Keep documentation and implementation local on the existing feature branch; do not create another worktree or publish without a separate reason/consent.

## File map

| File | Responsibility |
|---|---|
| `docs/sources/tr-hybrid-intelligence-tree.html` | UTF-8 source snapshot, inert input |
| `docs/sources/tr-hybrid-intelligence-tree.manifest.json` | Source and normalized artifact hashes and import scope |
| `.gitattributes` | Disable newline conversion for the pinned HTML only, preserving its checksum across checkouts |
| `trading_system/tree_spec/catalog.py` | Source units, bounded parser, open parameters, explicit blocked readiness |
| `trading_system/tree_spec/snapshot.py` | Typed definitions, observations and pre-entry time boundary |
| `trading_system/tree_spec/__init__.py` | Package description only |
| `tools/inspect_tree_source.py` | Read-only CLI, manifest integrity and readiness exit code |
| `tests/tree_spec/test_catalog.py` | Source preservation, extraction, corrupt/unsupported data handling |
| `tests/tree_spec/test_snapshot.py` | Time, phase, type, missingness, completeness and mutation boundaries |
| `AGENTS.md`, `README.md` | Discoverable active-plan memory |
| `agent-exchange/status/2026-09-08T*-codex-tree-replay-foundation.md` | Actual verification and next work |

## Task A1: Import evidence and expose an honest source catalog

Consumes the supplied HTML as bytes, not as executable instructions.
Produces `load_catalog(path: Path, expected_sha256: str | None = None) -> SourceCatalog`.
`SourceCatalog.units` is a tuple of `SourceUnit(unit_id, section, title, question,
checks, output, note, kind, line_start, line_end)`; IDs are namespaced by section
and zero-based source ordinal, stable only within the pinned source version.
`SourceCatalog.open_parameters` preserves all explicit parameter groups.
`SourceCatalog.readiness()` returns a JSON-ready report with `ready_for_replay=False`,
`ready_for_training=False`, section counts and explicit blockers.

- [x] Preserve source through apply_patch; record original-byte and stored-byte hashes.
  If newline normalization changes bytes, record both and the transformation explicitly.
- [x] Write real-source tests plus malformed inputs using temporary files. Example:

  ```python
  def test_unresolved_source_never_authorizes_training():
      report = load_catalog(SOURCE).readiness()
      assert report["ready_for_training"] is False
      assert "EXECUTABLE_TREE_NOT_IMPLEMENTED" in report["blockers"]
  ```

  Additional cases: question/check preservation including Hebrew; every expected
  guide section represented; duplicate/missing declaration rejected; malformed row,
  executable expression, count mismatch and wrong hash rejected; source line ranges
  resolve to the extracted evidence. Do not eval or launch the HTML.
- [x] Run the catalog tests (in `python -m pytest tests/tree_spec -q`) and observe failure
  because the new package/API does not exist before implementing it.
- [x] Implement strict version-specific extraction of `layers`, `trRows`,
  `trKnowledgeRows`, `sharedRows`, `ofRows`, `optionsRows`, `runtimeRows`,
  `governanceRows`. Accept only string-valued fields and data arrays in these
  declarations; fail on unsupported syntax rather than silently dropping content.
  Preserve the full `checks` string without claiming its clauses are atomic features.
- [x] Implement `python tools/inspect_tree_source.py`: resolve source from the
  repository manifest, verify hash, emit JSON to stdout, no file/data/network mutation.
  `--require-ready` exits 2 for unresolved replay/training; parse/integrity errors exit 1.
  Normal inventory inspection exits 0 even when readiness is false. `--include-units`
  adds full source text/lineage to stdout; default output is a compact summary.
- [x] Run tests and both CLI modes; verify that inspection succeeds but readiness fails.
- [x] Review diff and record verified task status. Do not commit or push as part of
  this initial local handoff; use the project's integration workflow when requested.

## Task A2: Validate a pre-entry snapshot without domain guesses

Consumes explicit `FeatureDefinition(feature_id, dtype, unit, phase, required)` and
`FeatureObservation(feature_id, value, status, observed_at, available_at, source)`.
Valid dtypes: `number`, `boolean`, `category`; phases: `PRE_ENTRY`, `POST_ENTRY`,
`OUTCOME`; availability: `KNOWN`, `UNKNOWN`, `UNAVAILABLE`, `NOT_APPLICABLE`, `STALE`.
Only PRE_ENTRY definitions may enter this builder.

Produces `build_snapshot(snapshot_id, decision_time, definitions, observations) ->
PreEntrySnapshot`, with immutable tuples, `eligible` and `blocking_features`.
`to_payload()` emits separate `features` and `availability` maps plus provenance;
it does not emit labels or declare eligibility to train/replay the entire tree.

- [x] Write failing tests before implementation. Example:

  ```python
  def test_future_publication_cannot_enter_pre_entry_snapshot():
      item = replace(known_observation, available_at=T + timedelta(seconds=1))
      with pytest.raises(ValueError, match="future"):
          build_snapshot("s1", T, (definition,), (item,))
  ```

  Cover future observation; naive datetimes; publication before observation;
  duplicate/unknown/missing feature; OUTCOME/POST_ENTRY role; non-finite numbers;
  bool vs numeric type; non-null unavailable values; required missing blocker;
  optional missing preserves None; known False/0 preserve their distinct types;
  mapping/collection values rejected; changing caller-owned lists cannot mutate snapshot.
- [x] Run the snapshot tests (in `python -m pytest tests/tree_spec -q`) and inspect missing-package failures before implementation.
- [x] Implement scalar-only frozen dataclasses and boundary validation. Require all
  declared features to have observations; absence must be explicit, not silently omitted.
  For a missing observation, timestamps describe when absence was evaluated; no
  fabricated market observation/value is supplied. Reject future or internally
  inconsistent declared timestamps. Serialize timestamps normalized to UTC.
- [x] Keep metadata validation distinct from proof of provenance. The builder cannot
  detect a mislabeled outcome column or a producer that lies about timestamps. Atomic
  registry review, dependency lineage, as-of feed adapters and replay tests remain required.
- [x] Run new tests plus regression suites for features/candidates/datasets/models/evaluation.
- [x] Review and document behavior, limitations and next domain-dependent tasks.

## Task A3: Persist memory and independently check this initial slice

- [x] Link the master plan and this execution plan from AGENTS.md and README.md.
- [x] Use requesting-code-review for a read-only review of this uncommitted slice;
  no reviewer may mutate files, branch state or spawn another reviewer.
- [x] Address significant findings with failing regression tests first.
- [x] Run `python -m pytest tests/tree_spec -q`, attempt `python -m pytest -q`,
  `python tools/inspect_tree_source.py`, and `git diff --check` with fresh outputs.
  Record environmental/unrelated failures honestly instead of claiming all pass.
- [x] Record actual results in agent-exchange/status using result.md format,
  referencing the current direct user request, not a fabricated inbox request.
- [x] Prepare handoff links, exact implemented boundary, tests and remaining domain inputs in the status record.

### Verification scope adjustment during execution

The full `python -m pytest -q` run was intentionally stopped after roughly eight
minutes while executing legacy phase-validator subprocesses. No test failure had
been emitted, but this is NOT a full-suite pass. The final regression substitutes
`python -m pytest -q --ignore-glob='*validator*'`, in addition to all 63 new tests
and the 91 feature/candidate/dataset/model/evaluation tests. Only the identified
test runner and its validator child were stopped. The status record reports
actual results; omitted legacy validators remain an explicit verification limit.

Result: **443 passed**, including **63 new tests**; the separate scoped regression
also passed 91 tests. The omitted 56 legacy validator tests are not claimed to pass.
Initial tasks A1–A3 accepted after independent review and correction of DST-fold
ordering and null-hash defects. See
`agent-exchange/status/2026-09-08T172600Z-codex-tree-replay-foundation.md`.
Next work is phase B; source inventory must not be mistaken for its completion.

## Subsequent phases: implementation contracts, not assumed completed work

The master plan defines phases B–J. Before each coding slice, expand its approved
domain decisions into a separate executable plan; do not invent formulas to make
this initial plan look complete. The following engineering boundaries are fixed:

| Phase | Planned files / boundary | Required acceptance evidence |
|---|---|---|
| B | `configs/trees/tr-hybrid-node-contracts.yaml`, `schemas/tree_node_contract.schema.json`, `tests/tree_spec/test_node_contracts.py` | Every selected graph dependency maps source → formula → test; OPEN dependencies prevent compilation; graph nodes/edges cross-checked |
| C | `trading_system/tree_replay/state.py`, `features.py`, `candidates.py`, `tests/tree_replay/test_golden_scenarios.py` | Sagiv's positive/negative/wait fixtures match observable node traces; only as-of inputs; explicit graph/version |
| D | Extend the same engine by source family, separate `order_flow.py`, `options.py`; approved data adapters | Full coverage report, missing feed behavior and independent OF candidates; no fake DOM/options |
| E | `trading_system/tree_replay/lifecycle.py`, `labels.py`, `tests/tree_replay/test_lifecycle.py` | Entry/expiry/partial/stop/target/scale/BE/invalidation and costs; outcome horizon and conservative ambiguity rules |
| F | `trading_system/datasets/tree_replay_dataset.py`, `tests/datasets/test_tree_replay_dataset.py` | Normalized entities, feature allowlist, deterministic checkpoint/resume, source hashes, no duplicated episode leakage |
| G | `trading_system/models/tree_outcome.py`, `trading_system/evaluation/tree_temporal_split.py` | Purged chronological folds; rule-only/logistic/CatBoost/LightGBM comparisons; independent calibration; explicit model dependency lock |
| H | `trading_system/evaluation/tree_portfolio.py`, model card and immutable experiment manifest | Locked holdout, retained coverage, net_R/drawdown/costs, rejection opportunity cost, uncertainty and era analysis |
| I | Separate shadow/promotion plan under project governance | Human authorization when required, no broker order from research code, rollback and drift evidence |
| J | Separate management/retrieval/candidate-generation research specs | No counterfactual claim from one observed policy; independent experiments |

Integration with existing schemas and feed policies must be reviewed per slice.
Specifically reconcile `configs/graphs/node-registry.yaml` layer meanings with
the pinned HTML: legacy L4 is Location/Levels, while source L4 is Market Memory.
Map feature status and computed/available timestamps explicitly against
`configs/features/feature-catalog.yaml`; no layer-number join or silent rename.
Proposed paths are ownership boundaries, not evidence these modules exist today.
