# Agent Exchange Review

Reviewer:
Codex scoped Task2 fix-round1 reviewer; no subagents.

Target request:
User-directed scoped re-review of findings 1/2 in
`agent-exchange/reviews/2026-09-09T110501Z-historical-frames-review.md`.
Original request: `agent-exchange/inbox/codex/2026-09-09T110501Z-historical-frames-review.md`.
Fix contract: `.superpowers/sdd/2026-09-09-historical-levelmap-core/task-2-fix-brief.md`.

Created at:
2026-09-09T11:13:04Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:

- Finding 1: ADDRESSED.
- Finding 2: ADDRESSED.
- Fix delta: PASS; no new breakage identified by static inspection. This is a scoped re-review, not a fresh whole-task review or durable acceptance.

Findings:

1. **ADDRESSED — required boundary regressions.**
   `tests/tree_replay/test_frames.py:164` adds two literal source-label cases: January 1 moves into December 31, and a one-day shift places the current label beyond decision time. All three rows retain literal observation/publication timestamps, frame timestamps remain January 3 00:10, and every non-label row field is compared with the original frame.
   `tests/tree_replay/test_frames.py:335` adds six shortened-coverage cases: daily/intraday late starts and early ends, plus daily coverage ending between periods and between active sessions. Interval clipping preserves valid schedule construction; supplied bars and required periods remain intact. Each case asserts the specific `CALENDAR_COVERAGE` blocker, empty rows and null observation/publication timestamps.
   `tests/tree_replay/test_frames.py:242` checks exact 1h/4h closes and the next forming bucket after one additional closed 5m bar. Complete literal dictionaries assert OHLC, volume, labels, boundaries, state and actual observation/publication. The fixture arithmetic supports the expected closed highs/closes of 113/112 and 149/148, and forming highs/closes of 114/113 and 150/149. Future supplied bars are excluded from expected rows.

2. **ADDRESSED — upsampling test reached the wrong guard.**
   `tests/tree_replay/test_frames.py:409` replaces the ineffective parameter branch with a dedicated construction check using empty bars, a 30m base and the existing 15m target. History and anchor are at midnight; periods are empty. Empty bars avoid the identity rejection at `trading_system/tree_replay/frames.py:68`, allowing the duration guard at line 98 to execute. The anchored error match is `^cannot upsample a coarser base timeframe$`; an unrelated `ValueError` cannot satisfy it.

Delta inspection:

Only the ineffective upsampling parameter/branch was removed; its replacement is stricter. The three added parameterized tests supply ten additional cases. Existing fixtures and unrelated assertions are unchanged. Expected values are literal, and there are no mocks or production changes in the fix delta. No new concern requires a focused runtime experiment.

Open questions:

None for findings 1/2 or this delta. Broader task/source/model readiness remains outside this review.

Recommended next action:

Controller may record durable acceptance using this scoped review and its independent test run. No further fix is requested for findings 1/2.

Verification reviewed:

- Read mandatory `AGENTS.md`, exchange README/protocol, inspected Codex inbox, and read the original request/review, review template, Task2 brief, fix brief, appended report and complete `task-2-fix-1.diff`. Inspected fixture and constructor context only to resolve the delta's assertions and guard path.
- `git status --short` confirmed the existing dirty/untracked workspace. Scoped `git diff -- tests/tree_replay/test_frames.py trading_system/tree_replay/frames.py docs/architecture/HISTORICAL-FRAMES-USAGE.md` was empty because these files are untracked; it was not treated as fix evidence.
- `git hash-object` confirmed before-test blob `d81ebff59dde6cfdd3056f2f50c8c47f8533ac9a` and current-test blob `fcae2be30241ae93096e2cba722d150eeae81797`, matching the supplied delta. Production blob `97c741b9d5d200bcf201d06d31ff6b35b069e5a2` and usage-document blob `aaed9b9aa44f7453b29f8a13f73af8ecbb76907d` match the original review and fix report.
- Reported worker PASS: `python -m pytest tests/tree_replay/test_frames.py -q --tb=short` — 69 passed in 0.72s, exit 0. User separately reports the parent independently reran 69 tests passing; exact parent timing was not supplied and is not needed for this review.
- No tests rerun by this reviewer, per the explicit scoped instruction; no unresolved doubt warranted a focused check. Historical RED claims were not recertified.
- This review file is the only reviewer write. No production edits, commits, worktrees, cleanup, subagents or durable exchange acceptance writes.
