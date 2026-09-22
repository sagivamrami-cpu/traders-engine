# Task 2 review: lifecycle OPEN zone-return source

Reviewer: Codex

Target request: Read-only independent review of Task 2 for the lifecycle OPEN
zone-return retained-source auditor and explicit-root CLI.

Created at: 2026-09-14T23:00:00Z

Status: REVIEW_READY_FOR_CODEX

## Verdict

**PASS**

## Findings

No blocking or material findings.

- The retained snapshot is correctly identified through
  `chart-desk/chartdesk/tracker.py`: its repository HEAD is
  `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9` and its blob is
  `b616b34022e436545d8c1daf85eced51614fd74e`.
- The auditor pins and AST-compares the exact helper slice (1046--1106) and
  live-call boundary (2751--2759). It rejects no-excursion, target-only
  rearm, directional-band, recheck, ordered-message, caller-order, source
  identity and runtime-projection drift.
- The runtime projection requires the actual `Revalidation(source)` child and
  its `still_valid(trade)` call, plus the sole direct
  `zone_return_at` mutation. Its child audit graph requires accepted
  lifecycle-transitions, lifecycle-primitives (entry band, DeskSuccess and
  voice), and revalidation projections.
- The intake and usage accurately preserve the inherited revalidation boundary:
  the child may fetch corrected evidence and attempt source-owned shadow
  writes. The narrower zone-return claim is accurate: its own direct behavior
  is advisory and writes only `zone_return_at` on emission.
- The CLI requires an explicit source root, emits schema-valid `BLOCKED` JSON
  with both readiness flags false for missing roots, malformed reports,
  parsing/audit errors and serialization failure, and exits zero only for a
  verified report.

## Scope notes

The path written in the review request as `chart-desk-app/strategies/tracker.py`
does not exist in the retained snapshot. The task artifacts consistently use
the actual pinned location, `chart-desk/chartdesk/tracker.py`, which was read
as text only. This review does not establish a full OPEN resolver, persistence,
delivery, fills/economics, replay, dataset, training, model, or live-trading
readiness.

## Recommended next action

Proceed to the required final review and Codex acceptance decision for this
bounded source-audit component.

## Verification reviewed

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py tests/tree_spec/test_lifecycle_open_zone_return_source.py -q --tb=short -p no:cacheprovider
```

PASS: `39 passed in 20.22s`.

```powershell
python -B -m pytest tests/tree_replay/test_lifecycle_open_zone_return.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_revalidation.py tests/tree_spec/test_lifecycle_open_zone_return_source.py -q --tb=short -p no:cacheprovider
```

PASS: `189 passed in 24.34s`.

```powershell
python -B tools/check_lifecycle_open_zone_return_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
```

PASS: `VERIFIED`; helper, live-call, runtime and required child projections
verified; both readiness flags remain `false`.

Missing-root and missing-argument CLI probes each returned exit `2` with valid
`BLOCKED` JSON and both readiness flags `false`.
