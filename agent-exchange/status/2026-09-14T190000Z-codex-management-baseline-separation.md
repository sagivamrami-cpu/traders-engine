# Agent Exchange Result

Target: Codex / project team

Sender: Codex

Created at: 2026-09-14T19:00:00Z

Request: Active goal — continue the approved outcome-learning and dynamic-management plan.

Status: ACCEPTED_BY_CODEX

Summary: Verified and recorded that the research-only chart-desk management
trial's partial-exit `CONTROL` is not the approved fixed-full-TP1 economic
baseline. The plan now requires separate policy IDs, horizons and labels before
any J3/J4 simulation or training view is produced.

Changed files:

- `docs/architecture/MANAGEMENT-SOURCE-MAPPING-INTAKE.md`
- `docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md`
- `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md`
- `agent-exchange/reviews/2026-09-14T190000Z-codex-management-baseline-separation.md`
- This status record.

Verification results:

- PASS: the approved baseline decision states `full exit at TP1` with no
  partial exits, additions, optional BE or trailing.
- PASS: the audited source's `management_trial.py` has a distinct `CONTROL`
  arm with 25% / 25% / 50% weights.
- PASS: assertions confirm that source, master plan and mapping preserve the
  separation; Markdown whitespace validation passed.

Decisions needed:

None for this correction. The existing J1/J2 domain decisions and the J3
fill/cost/horizon contract remain necessary for implementation.

Blockers:

This closes a research-integrity ambiguity only. It does not make either
policy executable, create labels, authorize broker behavior or complete J3–J7.

Recommended next action:

Obtain the pending J1/J2 decisions, then implement a simulator that retains
policy identity per episode/action and compares dynamic policies with
`fixed_full_tp1_v1` at equal conditions.

Notes:

No runtime source code was changed.
