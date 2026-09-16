# Task1 fix report — I1 / M1

Target: Codex controller
Sender: Codex scoped test-fix implementer
Created at: 2026-09-10 19:28:00 UTC
Request: agent-exchange/inbox/codex/2026-09-10T192400Z-tree-walk-test-fix.md
Status: IMPLEMENTED_AWAITING_CODEX_REVIEW
Result: DONE; no implementation blocker or runtime defect found in this scope.

## Scope and startup

Read AGENTS.md, exchange README/protocol, listed the Codex inbox, and read the
scoped request, complete 191914Z review (I1/M1), Task1 brief/report and binding
TREE-WALK-READER-CONTRACT.md. Used receiving-code-review guidance to verify the
findings before edits. Existing dirty checkout was preserved. Only these files
were written, using apply_patch:

- tests/tree_replay/test_tree_walk.py
- .superpowers/sdd/2026-09-10-tree-walk-reader/task-1-fix-report.md

No nested agents, reviewer, commits, data/live actions, runtime edits or Task2
suite runs. Retained source was read as text only, never imported or executed.
The authoritative retained source inspected was under
`C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk/chartdesk/`:
tree.py MEMORY, FirstVector and both geometry functions; tr.py vector_zones.
The earlier ordinary sibling checkout inspection was not used as the pinned
authority. Local actual dependency code supplied the map/pricing/trace formulas;
expected results were written from those rules before running the tests.

## I1: literal memory and complete geometry outcomes

The 15-row memory tape starts with ten bars O/C100, H101, L99, V100. The five
following OHLCV rows are literal in memory_tape; no derived values are supplied
to any reader. Row10 has green body100..102, V300 >= twice the prior100 mean.
Row11 departs above it. Row12 has red body104..108, V1000 >= twice the prior120
mean. Row13 returns through green (one touch), while departing below red.
Row14 either stays above red or returns through it. No other bar reaches a
climax threshold: later spread-volume is below the earlier climax maximum and
later volume100 is below twice its prior mean.

Assertions check both actual zone rows, their time, bottom/top, kind, open flag
and touches. The full Walk must retain exactly [(106., 'red', 0)] in the open
case, excluding the cleared green zone; the cleared case must retain [].
Both full walks complete all 12 stages. Memory fact text and the exact count of
the observed-empty missing entry are asserted, separately from EQH/EQL facts.
For the open case, ATR starts2 and consumes true ranges4,3,6,5,10 at alpha1/14:
ATR=53449/16807=3.1801630273; distance4/ATR=1.25779715 rounds to1.3 in the fact.
The cleared case reports the source's observed-empty fact, not an unread result.

The existing long/short raw-map geometry test now checks the entire target list
and every Plan obstacle, and the entire returned levels_to_trade target list:

- Long stop99.7, targets Q-QUARTER125 and Q-HALF150; merged ADR-HI/RD-HI115 obstacle.
- Short stop119.5, targets merged ADR/AWR/RW/AMR/RD low95; merged ADR50/AWR50/AMR50,
  YDAY/D2/D3/D4/LWEEK low90; then Q-QUARTER75.
- Short obstacles NY-OPEN107, LONDON-OPEN103, and the merged100 rung containing
  YDAY-CLOSE, DAY-OPEN, WEEK-OPEN, EMA200-1h, EMA800-1h, CLOUD50-4h, EMA200-4h,
  Q-WHOLE. Each merged name is asserted, including multiplicity.

Derivation: previous period ranges20; today's95+20=115 and115-20=95; current
week/month90+20=110 and115-20=95; open100 +/-10 produces110/90. Old lows are90.
The25-point quarter grid supplies75/100/125/150. Gold entry zone108..112 excludes
110. Stop widening from the zone edge gives100.5 long before the100 quarter
snap minus .15*ATR=.3, hence99.7; short zone edge112 plus7.5 gives119.5.
At MIN_RR1.2, long risk10.3 needs12.36 reward and short risk9.5 needs11.4.
This separates the listed obstacles from paying rungs. TP1 is below2R on both
sides, so there is no measured-rung insertion. Price and rung order are checked;
only the order of names inside a merged rung is normalized, because the flat100
seeded EMA arithmetic can differ by floating-point roundoff. Sorting name lists
preserves duplicate detection (no set conversion).

## M1: raw trace and named boundary cases

RawSource.read_report/read_tv_csv now append their artifact attempt before
raising. Two tests assert those failure traces. Successful house and strict
walks assert a complete literal ordered fetch/artifact/clock trace, including
constructor silence, separate news/session/Brinks/PSY clocks, strict pivot read,
repeated 1h/15m requests, and actual caught raw-fetch failures. Empty report
listing correctly causes no report/TV read in this full-walk fixture.

Added a raw4h OSError after successful15m, requiring the exact DATA stop and only
those two reads; blue-at-low and violet-at-high committed-side trap cases; and
four FirstVector cases (both sides, prior break at i-6 versus i-7). With i118,
index112 is included in the six-close window;111 is excluded. Flat128 followed
by150/106 first moves EMA by +/-22*2/51 and cloud width by22*sqrt(.0099)/4, so
that prior close breaks its cloud. Intervening128 closes are within the relevant
edge; the completed140/116, V250 bar qualifies. The existing ordinary cloud-
equality test was preserved without duplication.

## Candidate-only mutation proof

Eleven parametrized probes compile only the local candidate TreeReader class
into a fresh namespace copied from its local module bindings. They never write
the candidate or alter the imported runtime module. Each mutation must bind one
exact candidate text site; the six-close probes replace the whole local block
so price and cloud slices stay aligned. The same literal assertion helpers used
by normal tests must raise AssertionError; compilation errors or unrelated
runtime exceptions do not count as successful detection.

Detected mutations: drop-zone-handoff; zone-top-not-midpoint; wrong-zone-kind;
wrong-touch-count; erase-observed-empty; drop-plan-obstacles;
truncate-plan-targets; truncate-geometry-targets; reverse-ladder-reads;
exclude-sixth-close; include-seventh-close. All eleven were rejected by the new
outcome/trace assertions. This is focused Task1 sensitivity proof, not Task2's
source/dependency audit or independent component acceptance.

## Verification and hashes

Exact focused command:

```text
python -B -m pytest tests/tree_replay/test_tree_walk.py -q --tb=short -p no:cacheprovider
```

Final terminal chunk83c133: **95 passed in7.25s, exit0**. This is84 ordinary cases
plus11 candidate-mutation cases,24 cases more than the supplied71-case baseline.
No test/runtime edits occurred during or after that final run. Earlier focused
terminal f4bd90:95 passed7.71s, exit0; final run followed comment/import cleanup
and strengthening merged-name comparison to retain multiplicities. No RED or
runtime failure was encountered in this fix round. Prior71-pass evidence was
provided by main, not independently rerun before editing.

A read-only comparison against Task1's packaged complete test addition found
509 baseline lines and725 current lines. Only five baseline lines were replaced
(the geometry test signature/reader binding/first-target-only assertions); all
other changes are additions. No trailing whitespace. Scoped git diff --check
passed, but the test file is untracked, so the package comparison is the useful
baseline diff. Runtime/usage SHA256 values match the frozen review values.

```text
tests/tree_replay/test_tree_walk.py
283ecc81227dadd2ae1d52769785b10e8877851abb8128874584467a65ef4dab
trading_system/tree_replay/_vendor/tree_core.py
17e6dfd69ead1c19ad1f60cf33d3b651a266873a188d68d697142511b10cc8d9
trading_system/tree_replay/_vendor/tree_signals.py
909b66e3961f1ca298fab030c9af5479fbe91e303aa09092f6fb3fbc950cc22a
trading_system/tree_replay/_vendor/tree_walk.py
c7ef95f30c7d83b6f98d59d767afd229a070cde1b295b989196f28283518d117
docs/architecture/TREE-WALK-READER-USAGE.md
ad001113da8e16b3adf07a1d65d551e8ceef825de702ec8ff06877727ef92c55
```

Decisions needed: none. Blockers/concerns: none within the scoped test fix.
Recommended next action: main's scoped re-review of I1/M1. Task2 and component
acceptance remain main's work; this report claims no full replay or readiness.
