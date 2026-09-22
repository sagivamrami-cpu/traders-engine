# Agent Exchange Review

Reviewer: Independent Codex Task1 reviewer (spec and quality; no nested agents)

Target request: agent-exchange/inbox/codex/2026-09-09T211924Z-revalidation-task-review.md

Created at: 2026-09-09T21:21:13Z

Status: REVIEW_READY_FOR_CODEX

Verdict: Spec compliance PASS for Task1; task quality Approved. No Critical, Important, or Minor findings.

Findings:

## Spec compliance

- All three requested additions are present in the supplied complete diff: runtime, behavioral tests, and usage. Required helpers and composed reader methods are implemented at `trading_system/tree_replay/_vendor/revalidation.py:18`, `:46`, `:66`, `:84`, `:92`, `:113`, `:136`, and `:152`.
- The runtime constructs actual TrackerAdmission, StretchReader, and EmaReader instances (`trading_system/tree_replay/_vendor/revalidation.py:86`). Bias flip precedes stretch, freshness, and shadows; missing core evidence preserves the allowed-but-unverified state (`:187`). Age uses separate requests and per-operation timestamps, normalizes each timeframe, and resets accumulated evidence on exception (`:215`). Shadow checks retain their order and do not change the final verdict (`:234`).
- Pending revalidation checks still_valid before its default clock and tree request, clamps negative age, preserves the two-hour boundary and opposing-direction precedence, and retains prior verification only with a clean tree reply (`trading_system/tree_replay/_vendor/revalidation.py:92`, `:113`). Calendar numeric precedence, raw nonfinite values, ISO fallback, input ordering, inclusive window, and original impact-string semantics are preserved in the implementation (`:18`, `:46`).
- Explicit raw ports, unknown-state caveats, unbound tree_walk, and the remaining full replay/model work are documented (`docs/architecture/REVALIDATION-SOURCE-USAGE.md:18`, `:34`, `:59`, `:65`). No expanded live behavior or public readiness claim appears in the three-file change.
- Cannot verify from this diff: independently pinned whole-source AST equivalence/substitution counts and inherited dependency audits. These belong to Task2 under `docs/architecture/REVALIDATION-SOURCE-CONTRACT.md`, not this Task1 approval. The reported EMA final acceptance is also external to this diff and must remain part of component acceptance intake.

## Strengths

- Tests supply real OHLC/volume frames and calculate TFViews with read_frame instead of replacing complete policy or numerical readers (`tests/tree_replay/test_revalidation.py:29`, `:46`, `:69`). They check actual same/opposite-direction stretch behavior, vector inclusion at the twelfth versus thirteenth bar, and a calculated bearish structure (`:322`, `:363`, `:377`).
- Literal threshold, missing-evidence, and precedence assertions cover the soft/hard age boundaries, normalized four-hour age, exception reset, early veto short-circuit, and tree uncertainty (`tests/tree_replay/test_revalidation.py:201`, `:230`, `:239`, `:250`, `:285`, `:300`, `:340`).
- The in-memory writer verifies JSON, Unicode, operation timestamps, effect ordering, and best-effort writer failures. Fetch order and default-versus-explicit clock behavior have explicit assertions (`tests/tree_replay/test_revalidation.py:277`, `:394`, `:408`, `:431`).
- One small policy module and one reusable raw-port fixture keep responsibilities clear. The 281-line runtime retains the specified original bodies while reusing existing calculation modules; the 496-line test file exercises independent behaviors rather than introducing a second policy implementation (`trading_system/tree_replay/_vendor/revalidation.py:84`; `tests/tree_replay/test_revalidation.py:46`).

## Issues

- Critical: None.
- Important: None.
- Minor: None.

Open questions:

- None blocking Task1. Task2 source/dependency certification and final component acceptance remain outstanding; this report does not certify causal feeds, complete tree_walk, historical replay, economics, or model readiness.

Recommended next action:

- Accept Task1 at the task gate and continue the already-scoped Task2 auditor work, followed by its independent review and final component acceptance.

Verification reviewed:

- Read the requested brief, contract, report, complete three-file diff, exchange startup documents, inbox, review template, and supplied task-reviewer rubric. The large combined tool response initially truncated part of the diff; recovered the omitted package ranges before judging them. No changed file was separately reread to judge its implementation. No broader source crawl, retained-source execution, nested agents, or duplicate suite.
- Implementer-reported command, not rerun: `python -B -m pytest tests/tree_replay/test_revalidation.py tests/tree_replay/test_ema_windows.py tests/tree_replay/test_stretch.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_calculations.py -q --tb=short -p no:cacheprovider`. Report `agent-exchange/status/2026-09-09T211455Z-revalidation-runtime-progress.md` records exit 0, 370 passed in 5.54s, clean current output, initial missing-module RED, and corrected test-only failures. These are reported results, not an independent suite run.
- Independently ran `Get-FileHash -Algorithm SHA256 'trading_system/tree_replay/_vendor/revalidation.py', 'tests/tree_replay/test_revalidation.py', 'docs/architecture/REVALIDATION-SOURCE-USAGE.md' | Format-List Path,Hash`: PASS. All three hashes exactly match the report: runtime `F11DC02C4CE8CE9E4CF7B387D8AE76FEBD8256D3B2559C985669534E227DE8D3`; tests `35AD02B24F5353667170088AEDE947155596E9BFAD51D0508CA2E2F3D1178328`; usage `1EFBB152234EB76D0AD646AC4EBDAC8C56CDF0897746588EB2D5F6DF638074EA`.
- Named doubt: existing main-flow fixtures use one timestamp value, so a focused probe checked whether independent timeframe clock values affect freshness and whether clean aged-tree agreement improperly upgrades prior unverified evidence (`trading_system/tree_replay/_vendor/revalidation.py:113`, `:215`; `tests/tree_replay/test_revalidation.py:90`, `:431`). The command below runs only the local fixture definitions and one additional composed scenario; it does not invoke pytest or retained original source. PASS, exit 0: the one-hour observation yields 21.001 equivalent minutes, four timestamp calls are consumed, the aged tree is called and agrees, and verified remains False. The first invocation's literal Hebrew assertion was corrupted by PowerShell pipe encoding after the boolean assertion had passed; the ASCII Unicode-escape assertion below corrected that probe-only issue. No repository file changed for either invocation.

```powershell
@'
import runpy
import pandas as pd
ns = runpy.run_path('tests/tree_replay/test_revalidation.py')
Ports, NOW = ns['Ports'], ns['NOW']
class AdvancingPorts(Ports):
    def __init__(self):
        super().__init__()
        self.clock_values = iter([NOW, NOW + pd.Timedelta(minutes=84.004), NOW, NOW])
    def now_timestamp(self, *, tz):
        self.calls.append(('timestamp', str(tz)))
        return next(self.clock_values).tz_convert(tz)
p = AdvancingPorts()
result = ns['api']().Revalidation(p).revalidate_pending(ns['trade'](age_s=7200), now=NOW.timestamp())
assert result[0] is True and result[2] is False, result
assert '\u05d4\u05e2\u05e5 \u05de\u05d0\u05e9\u05e8' in result[1], ascii(result)
assert ('walk', ns['SYMBOL']) in p.calls
assert [c for c in p.calls if c[0]=='timestamp'] == [('timestamp','UTC')]*4
print('PASS: independent 1h operation clock produces soft staleness; clean aged tree preserves verified=False; four timestamp calls consumed.')
'@ | python -B -
```

Assessment: Approved. The reviewed implementation matches Task1's policy and composition boundaries, with meaningful numerical and side-effect tests. Whole-source/dependency certification remains a separate Task2 gate.
