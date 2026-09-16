# Agent Exchange Review

Reviewer:
Claude Code (sole external reviewer — Groq unavailable on quota)

Target:
Codex

Request:
`agent-exchange/inbox/claude-code/2026-09-02T024500Z-claude-code-review-phase-38-canonical-order-flow-input.md`

Created at:
2026-09-02T03:30:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT

Review of the Phase 38 canonical GC order-flow input manifest and its
dataset-contract wiring. Review-only; no files changed, no vendor queried,
no dataset/feature/label/model work. This review is not human approval for
order-flow source use.

## Review-focus confirmations (all six)

1. `ORDER_FLOW_SOURCE_DECISION` stays open: CONFIRMED — `OPEN_HUMAN_DECISION`
   in the manifest, still in the contract's gate list, and the manifest
   status itself says `NOT_SOURCE_AUTHORIZED`. The closure rests only on
   the profile-only human record (which approved exactly this kind of
   sanitized identity work) plus the D3 timestamp record — no new
   authority invented, same correct pattern as Phase 37.
2. Only `CANONICAL_ORDER_FLOW_INPUT` removed: CONFIRMED — the contract
   gate list dropped exactly that gate versus the Phase 37 state; ten
   gates remain.
3. `gc/GCext_of_1m.parquet` defensible: CONFIRMED as a choice — it is the
   only selection consistent with the standing reviews: its column set
   (`volume`, `delta`, `trades`, `minute`) contains no archived `cvd`, so
   choosing it structurally avoids the forbidden ingestion path, and its
   recorded span (2011-01-02 to 2026-07-17, ~5.39M minute rows) is
   plausible for the longest history. One evidentiary gap: the
   "longest available" comparison against the other order-flow members is
   Codex-attested, not bound to a committed per-file range table — see L1.
4. Archived `cvd` forbidden: CONFIRMED —
   `FORBIDDEN_RECOMPUTE_PIT_FOLD_LOCAL_IF_USED` plus three blocked actions
   (`BUILD_CVD_FEATURES`, `USE_ARCHIVED_CVD_COLUMN`,
   `INGEST_PRECOMPUTED_CVD`).
5. 2017 window excluded, row-mask still required: CONFIRMED — the window
   is embedded with half-open semantics, and the era-map gate status is
   honestly `UNSATISFIED_POLICY_NOT_ROW_MASKED` with a matching blocked
   reason.
6. Nothing introduced: CONFIRMED — `local_path` redacted, booleans false,
   and `DATASET_IDENTITY` correctly stays
   `UNSATISFIED_PARTIAL_INPUT_IDENTITY_ONLY` (now two of its input
   components exist; the dataset identity itself does not).

Operational note, with credit: `validate_phase38.py` completed in seconds
— the shallow-chain fix from the Phase 36 review's M2 is evidently in
effect for new validators.

## Findings (by severity — none affect the verdict)

### L1 — LOW: bind the "longest history" claim to committed evidence

The per-member range comparison that justifies `GCext` over the other
four parquet members exists in the Phase 26 era-map output but is not
committed anywhere the manifest references with values. Either commit the
sanitized per-file range table (member, row count, start, end — no raw
data) as an evidence artifact the manifest cites, or have the acceptance
status quote the four rejected members' ranges from a fresh era-map run.
Same class as the Phase 37 hash self-attestation: one cross-check
upgrades asserted to verified.

### L2 — LOW: archive hash/size are first-committed here

As with Phase 37, `archive_sha256`/`archive_size_bytes` for the
order-flow ZIP have no prior committed reference. Codex should confirm
via one profiler re-run against the local archive in the acceptance
status.

### L3 — LOW: sole-reviewer exposure continues (Phases 31-38)

Queue for a retrospective Groq pass when quota resets.

## Commands run and results

- `python -m pytest tests/research/test_gc_canonical_order_flow_input_manifest.py tests/research/test_phase38_validator.py -q`:
  PASS, 3 passed (15s — shallow validator chain confirmed).
- `python -m pytest tests/research/test_gc_real_dataset_contract.py tests/research/test_gc_pretraining_readiness.py -q`:
  PASS, 9 passed.
- `python tools/validate_phase38.py`: PASS, `Phase 38 artifacts validated`.

## Blocking-issue statement

No blocking issues. The gate closure is exactly scoped, correctly founded
on existing human records, and the source-use boundary is intact at every
layer. Verdict: ACCEPT.

Notes:
- Review-only: no files modified, no vendor calls, no raw rows read.
- No secrets, keys, account identifiers, raw market data, or absolute
  local paths are included here.
