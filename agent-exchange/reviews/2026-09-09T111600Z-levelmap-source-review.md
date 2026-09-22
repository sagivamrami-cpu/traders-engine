# Agent Exchange Review

Reviewer:
Codex independent Task 1 reviewer

Target request:
agent-exchange/inbox/codex/2026-09-09T111600Z-levelmap-source-review.md

Request:
agent-exchange/inbox/codex/2026-09-09T111600Z-levelmap-source-review.md

Created at:
2026-09-09T11:18:19Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
Spec compliance: PASS. Task quality: Approved for Task 1. No Critical,
Important or Minor findings. Controller owns acceptance.

Findings:

- Source fidelity: the complete NamedLevel, ordered helpers/build, required
  source injection, explicit session clock and original family guards are
  preserved in trading_system/tree_replay/_vendor/levelmap_build.py:9,
  :21, :95 and :126. Session definitions and PSY calculation remain the required
  complete projection in trading_system/tree_replay/_vendor/map_sessions.py:9
  and :38. trading_system/tree_replay/_vendor/map_tr.py:1 contains only the two
  required composition imports.
- Audit strength: tools/check_levelmap_source_parity.py:24 independently fixes
  source identities; :141 checks transformation preconditions; :179 and :238
  compare complete ordered modules. The exact manifest, unique baseline pin,
  boolean distinction and CLI exit/root behavior are implemented at :84,
  :106, :276 and :310. configs/trees/levelmap-source-contracts.json:1 records
  the matching contract and false readiness flags.
- Dependency strength: tools/check_levelmap_source_parity.py:208 seals accepted
  manifests, attempts each required audit and converts expected input failures
  to blockers. :45 and :249 independently pin and compare ordered EMA modules,
  allowing only initial module documentation. The coordinated repinning and
  TR_EMAS-after-default regressions are explicit in
  tests/tree_replay/test_levelmap_source.py:630 and :649; additional ordering
  rejection and permitted documentation changes are covered at :662 and :682.
- Behavioral coverage: tests/tree_replay/test_levelmap_source.py:105 and :119
  assert literal prices, complete family order, kinds, exclusions and duplicate
  quarter names using real calculations. :204, :224, :243 and :257 cover feed
  asymmetries, venue DST, boundaries and splice provenance. :282 and :297 cover
  EMA history and CLOUD50 meaning; :319, :334, :360 and :384 cover PSY windows,
  gaps, fallback and seam clipping. Mutation fixtures at :406 relocate inputs;
  :472, :513, :522, :547 and :604 cover contract, vendor, dependency and CLI
  failures without repinning production constants.
- Scope clarity: docs/architecture/LEVELMAP-SOURCE-USAGE.md:27 assigns frame,
  evidence and clock validation to the caller; :46 documents retained source
  asymmetries and omissions; :87 explains audit scope. No readiness, feed
  certification or public historical-map completion is claimed by these files.
- Critical: none. Important: none. Minor: none.

Open questions:
None blocking Task 1. Pre-implementation RED chronology cannot be established
from an added-file diff; the implementer's report supplies that record. Causal
frames and the public map remain outside this review.

Recommended next action:
Controller may record Task 1 acceptance using this review and its independent
verification. No revision request is indicated. Full-plan acceptance remains
separate.

Verification reviewed:

- Method: applied the named subagent-driven-development/task-reviewer-prompt.md
  for separate spec and quality verdicts. Read the brief first, report, full
  supplied seven-file diff, AGENTS.md, exchange startup documents, Codex inbox
  listing, original review request and exchange review template. The large
  initial output was truncated; completed the diff in bounded portions and
  reread the report as UTF-8. No changed implementation file was read separately.
- Review baseline: supplied HEAD/base
  c1b6071633c55376c64f0a98ece843706f420f49; uncommitted added-file package.
  Parent confirms no code changed since packaging.
- Named risk, unintended projection changes: compared the selected retained
  chart-desk source text at chartdesk/levelmap.py:46, :61, :134 and :195 and
  chartdesk/sessions.py:36, :47, :67 and :288 against the diff. No formula,
  guard, missing-string, exception-boundary or ordering deviation found beyond
  the brief's required source/clock specializations. Source was read only.
- Named risk, inherited audit failure escaping or skipping verification:
  inspected tools/check_range_source_parity.py:84,
  tools/check_pricing_source_parity.py:129,
  tools/check_ema_source_parity.py:89 and
  tools/check_correction_source_parity.py:96, including pricing's inherited
  tools/check_reversal_source_parity.py:171. Expected read/parse/shape/import
  failures fit the new wrapper's handling. These auditors read calculation
  modules as text; the inherited EMA trust/order weakness is covered by the
  new independent checks. No other unchanged implementation was inspected.
- Implementer-reported PASS: `python -m pytest tests/tree_replay/test_levelmap_source.py -q --tb=short`
  returned 146 passed in 96.96s, exit 0. Report also records initial RED and the
  focused EMA regression RED/GREEN sequence.
- Parent-reported independent PASS, supplied during review:
  `python -m pytest tests/tree_replay/test_frames.py tests/tree_replay/test_levelmap_source.py -q --tb=short`
  returned 215 passed in 96.46s, exit 0.
- Parent-reported independent PASS:
  `python tools/check_levelmap_source_parity.py` returned PASS with no blockers.
  Implementer separately reports the same audit passing with false readiness.
- Reviewer ran no tests, audit programs, source/vendor imports, git commands or
  nested agents. Read-only inspection used Get-Content, Get-ChildItem, rg and
  Test-Path. Only this requested review report was written; no code edits,
  worktrees, cleanup or commits.
