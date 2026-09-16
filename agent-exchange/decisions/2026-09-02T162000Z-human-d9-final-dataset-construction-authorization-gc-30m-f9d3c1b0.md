# Human Decision

Approver: Human Data Owner (decision delegated to Claude Code in the active
Claude Code session; see Evidence)

Created at: 2026-09-02T16:20:00Z

Scope: Authorize construction of exactly one identified research dataset, the
first real GC 30m dataset, per the D9-final rule
(`agent-exchange/decisions/2026-09-02T052006Z-human-d9-final-dataset-construction-authorization.md`).

Decision: APPROVED

Bound dataset identity:
- dataset_name: `gc-30m-real-research-dataset`
- dataset_id: `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966`
- identity manifest: `configs/datasets/gc-30m-real-dataset-identity-manifest.json`
  (manifest_id `ce3be8b21feb3702fbcd98377719b4b9314493ebd3313b93eff0b06fbada4171`,
  identity_source `LOCAL_ARCHIVE_VERIFIED`)
- input archives (sha256, verified against the local files):
  - OHLCV 1s ZIP `b59a9dd08a317162024d53c4f0841a68d68e51dfb66f5d9d62b140304c24c3d1`
  - order-flow ZIP `34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155`,
    member `gc/GCext_of_1m.parquet` only
- builder: `trading_system.research.gc_real_dataset_builder`
  (`gc-30m-real-dataset-builder-0.1.0`), rule constants hashed into the id

Authorized:
- One build of the dataset identified above, through
  `tools/build_gc_30m_real_dataset.py`, which must recompute the identity
  against the local archives and refuse to build on any mismatch.
- Order-flow exclusion solely through
  `trading_system.research.gc_order_flow_row_mask_cumulative_policy.apply_gc_order_flow_training_mask`.
- Row exclusion per `configs/data/gc-missing-bar-policy.yaml` (fail-closed,
  no forward fill), labels per D7-final, splits per D8-final.

Constraints:
- This authorization applies to `dataset_id`
  `f9d3c1b0d02da255a89dcbd01033106c51da389e25bb38f3307b9b1dc0c6e966` only.
  Any change to an input archive, governing config, schema, or builder rule
  produces a different id and requires a new record.
- The build manifest must emit excluded-row counts by reason and by split,
  missing-expected-bar counts by split and by trade date, and the parquet
  sha256, and must not contain local paths or raw market rows.
- Training is not authorized by this record. `training_start_allowed` may
  become true only through the pretraining-readiness gate after the built
  dataset passes `evaluate_training_readiness` for the baseline policy.
- Model promotion, live trading, broker execution, capital allocation, CVD /
  cumulative-delta features, HHLL primary labels, random splits, macro and
  options features remain blocked.
- Dataset manifests and any model card must carry
  `contract_identity_status: UNDECLARED_PENDING_RESEARCH` (D5-final).

Evidence:
- D9-final precondition met: pretraining readiness run
  `report_id 50261ee5977716478b97b324709e623616028a3687bf0ae53f0c5dbd352c9a37`
  (`2026-09-02T16:17:28Z`) reported `required_pretraining_gates` exactly
  `[DATASET_CONSTRUCTION_AUTHORIZATION, REAL_DATASET_NOT_BUILT]`, i.e. every
  other pretraining gate (SESSION_CALENDAR, MISSING_BAR_POLICY, ROLL_POLICY,
  DATASET_IDENTITY, ORDER_FLOW_SOURCE_DECISION, LABEL_CONTRACT,
  SPLIT_AND_EMBARGO_POLICY) satisfied, `blocking_reviews: []`.
- Human instructions in the active Claude Code session, 2026-09-02:
  "קבל החלטה ותבצע אותה" ("make the decision and execute it") and
  "תמשיך עד אשר הגענו למצב שאפשר להתחיל לאמן" ("continue until we reach a
  state where training can start"), delegating the remaining gate decisions
  to Claude Code.
- MISSING_BAR_POLICY closure: `configs/data/gc-missing-bar-policy.yaml`,
  `tests/research/test_gc_real_dataset_builder.py` (fixture-proven fail-closed
  exclusion), `tests/research/test_gc_missing_bar_policy.py`.
- DATASET_IDENTITY closure: `configs/datasets/gc-30m-real-dataset-identity.yaml`,
  `tests/research/test_gc_dataset_identity.py`.
- Plan: `docs/superpowers/plans/2026-09-02-phases-43-47-gc-real-dataset-to-training-start.md`.
