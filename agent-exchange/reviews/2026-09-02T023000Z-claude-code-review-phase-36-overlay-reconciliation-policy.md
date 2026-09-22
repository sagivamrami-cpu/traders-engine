# Agent Exchange Review

Reviewer:
Claude Code (sole external reviewer — Groq unavailable on quota)

Target:
Codex

Request:
`agent-exchange/inbox/claude-code/2026-09-01T213500Z-claude-code-review-phase-36-overlay-reconciliation-policy.md`

Created at:
2026-09-02T02:30:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT

Review of the Phase 36 GC calendar overlay/reconciliation policy
candidate. Review-only; no files changed, no vendor queried, no calendar
constructed or registered, nothing resampled or built. This review does
not authorize a session calendar and is not human approval.

## Review-focus confirmations (all six)

1. Policy candidate only: CONFIRMED — status
   `OVERLAY_RECONCILIATION_POLICY_CANDIDATE_REQUIRES_EVIDENCE`; nothing
   implements an overlay or reconciliation.
2. Observed gaps blocked as schedule authority: CONFIRMED — new blocked
   action `USE_OBSERVED_GAPS_AS_SCHEDULE_AUTHORITY`, the exact side-door
   this chain of reviews has guarded against.
3. Overlay and reconciliation tables unimplemented: CONFIRMED — both
   `REQUIRED_NOT_IMPLEMENTED`, with honest blocked reasons including
   `FULL_FINE_GAP_PROFILE_PENDING` and the profile status field candidly
   set to `BOUNDED_SMOKE_ONLY_FULL_PROFILE_PENDING` — the policy does not
   overstate what Phase 35 produced.
4. `SESSION_CALENDAR` unsatisfied: CONFIRMED —
   `UNSATISFIED_OVERLAY_RECONCILIATION_POLICY_ONLY`, registration guard
   active through the chained validators.
5. Nothing new introduced: CONFIRMED — all four booleans false; the five
   overlay types (holiday, special hours, maintenance, DST, venue halt)
   and five reconciliation controls (source attribution per overlay,
   scheduled-vs-observed separation, disagreement reason codes, human
   review for unexplained gaps, content hash/capture manifest) match the
   construction policy and prior review requirements exactly.
6. Sanitized CLI: CONFIRMED — constants and repo-relative refs only;
   tested.

## Findings (by severity — none affect the verdict)

### M1 — MEDIUM (carried): Phase 35 vectorization is now on the critical path

The gap profiler's Python-level per-row loop is still in the tree.
Acceptable for this policy-only phase — the policy honestly marks the
full profile as pending — but the NEXT step (implementing the
reconciliation table) requires the complete ~104M-row profile, which the
current implementation cannot produce in reasonable time. The Phase 35
review's vectorization fix must land before or with the reconciliation
implementation. This is the second phase carrying the item.

### M2 — MEDIUM: validator-chain runtime now exceeds practical windows

The four verification commands for this review exceeded a 10-minute
foreground window and had to complete in the background (~11 minutes
total; all passed). The recursive chain (36→35→34→33→32→31→...), each
layer re-running pytest, has crossed from flaky (three transient failures
observed in prior reviews) to operationally expensive. Restating with
urgency: new phase validators should chain only the previous phase's
schema and guard checks; the full stack belongs to the `foreach 0..N`
acceptance sweep. Without this, every future review and CI run pays a
superlinear cost.

### L1 — LOW: sole-reviewer exposure continues (Phases 31-36)

Queue the D2 chain for a retrospective Groq pass when quota resets.

## May Codex proceed to dataset identity/canonical input gates in parallel?

YES. `DATASET_IDENTITY`, `CANONICAL_OHLCV_INPUT`, and
`CANONICAL_ORDER_FLOW_INPUT` are independent of the session calendar and
may be advanced as policy candidates in parallel, provided: each resolves
only via its own human decision record; `SESSION_CALENDAR` (and
`MISSING_BAR_POLICY`, which depends on it) remain unsatisfied in the
dataset contract throughout; and no parallel phase treats calendar
metadata as available before the calendar exists.

## Commands run and results

- `python -m pytest tests/research/test_gc_calendar_overlay_reconciliation_policy.py tests/research/test_phase36_validator.py -q`:
  PASS, 3 passed.
- `python tools/validate_phase36.py`: PASS, `Phase 36 artifacts validated`.
- `python tools/validate_phase35.py`: PASS, `Phase 35 artifacts validated`.
- `python tools/validate_phase34.py`: PASS, `Phase 34 artifacts validated`.
- (Combined run completed in background after exceeding a 600s foreground
  window — see M2.)

## Blocking-issue statement

No blocking issues. All six review-focus items hold; the policy is honest
about every unbuilt piece. M1 and M2 are required operational fixes for
the next implementation step, not defects in this artifact. Verdict:
ACCEPT.

Notes:
- Review-only: no files modified, no vendor calls, no raw rows read.
- No secrets, keys, account identifiers, raw market data, or absolute
  local paths are included here.
