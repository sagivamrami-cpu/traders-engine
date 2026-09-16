# Human Decision

Approver: Human Data Owner (decision delegated to Claude Code in the active
Claude Code session; see Evidence)

Created at: 2026-09-02T13:00:00Z

Scope: Resolve Claude Code Phase 42 review finding F2. Define what satisfies
the `SESSION_CALENDAR` gate for `cme-globex-metals-research-v1` (v1), and
where the D2-final "dated overlay/reconciliation table" requirement and the
holiday / special-hours / venue-halt encoding now live.

Decision: APPROVED

Decided:
- `SESSION_CALENDAR` v1 is satisfied by the registered
  `cme-globex-metals-research-v1` calendar encoding normal GC Globex hours
  (Sunday-Friday, 17:00 CT open, 16:00 CT close), the 16:00-17:00 CT daily
  maintenance break, DST via `America/Chicago`, and trade-date roll, as
  implemented in Phase 42.
- The D2-final requirements to encode holidays, special hours, venue halts,
  and required overlays, and to create a dated overlay/reconciliation table
  with source attribution, are transferred out of the `SESSION_CALENDAR` gate
  into the `MISSING_BAR_POLICY` and dataset-manifest gates. They remain
  required before dataset construction; they are no longer a condition of
  `SESSION_CALENDAR`.
- This amends the scope of
  `agent-exchange/decisions/2026-09-02T052000Z-human-d2-final-session-calendar-implementation.md`
  only for the two constraints named above. All other D2-final constraints
  stand.

Constraints:
- The v1 calendar remains research-only and is not execution truth.
- Observed activity is not schedule authority.
- Databento `status` schema remains not queried (per
  `agent-exchange/decisions/2026-09-02T061500Z-human-d2-final-databento-status-schema-skip.md`).
- `holidays`, `early_closes`, and `special_sessions` for
  `cme-globex-metals-research-v1` stay empty until the overlay semantics are
  defined under the missing-bar policy; Phase 42 review F5 (holiday keyed by
  local date, not trade date) must be resolved before any of them is
  populated.
- The overlay/reconciliation table, when built, must carry source attribution
  per date or era and a source content hash or pull manifest, as already
  listed in `configs/data/gc-session-calendar-construction-policy.yaml`
  `reconciliation_requirements`.
- Dataset construction, resampling, real label/split construction, model
  training, model promotion, live trading, broker execution, and capital
  allocation remain blocked. Remaining pretraining gates are unchanged:
  `MISSING_BAR_POLICY`, `DATASET_IDENTITY`,
  `DATASET_CONSTRUCTION_AUTHORIZATION`, `REAL_DATASET_NOT_BUILT`.

Evidence:
- Human instruction in the active Claude Code session, 2026-09-02, after
  reading the Phase 42 review and its F2 question: "קבל החלטה ותבצע אותה"
  ("make the decision and execute it"), delegating this scope decision to
  Claude Code.
- Prior human narrowing in the same direction:
  `agent-exchange/decisions/2026-09-02T061500Z-human-d2-final-databento-status-schema-skip.md`
  ("Resolve actual missing bars, holiday gaps, and special-hour gaps through
  the later missing-bar policy and dataset manifest gates").
- Claude Code Phase 42 review raising F2:
  `agent-exchange/reviews/2026-09-02T124500Z-claude-code-review-phase-42-gc-session-calendar-registration.md`.
- Codex Phase 42 result:
  `agent-exchange/status/2026-09-02T062500Z-codex-phase-42-gc-session-calendar-registration-result.md`.
