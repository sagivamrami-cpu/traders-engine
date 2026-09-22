# Human Decision

Approver: Human Data Owner

Created at: 2026-09-02T05:20:05Z

Scope: Approve v1 chronological walk-forward split and embargo policy for the
first real GC 30m research dataset.

Decision: APPROVED

Policy:
- No random split.
- Train, validation, and test windows are ordered by time.
- Purge labels whose future horizon overlaps validation/test windows.
- Embargo size is at least the max label horizon, initially `8` bars.
- Scalers, imputers, encoders, normalizers, and feature transforms fit only
  inside the training window for each fold, then apply forward to validation
  and test windows.
- Apply the same 2017 damaged-window exclusion to every dataset variant.

Constraints:
- This record authorizes implementation of deterministic split manifests.
- This record does not approve unembargoed splits, random time-series splits,
  live trading, broker execution, or capital allocation.

Evidence:
- Human approval in active Codex session: "כל הסעיפים מאושרים מבחינתי".
- Human condition in active Codex session: "ניתן להתקדם רק אחרי שקלוד ואתה מסכימים".
- Claude Code review: `agent-exchange/reviews/2026-09-02T051500Z-claude-code-recheck-phase-40-human-decision-packet.md`.
- Codex decision packet: `agent-exchange/inbox/human/2026-09-02T040000Z-human-phase-40-remaining-training-gate-decisions.md`.
