# Codex status — outer admission Tasks 3–4

- Timestamp: 2026-09-14T23:05:00Z
- Status: REVIEW_REQUESTED
- Plan: `docs/superpowers/plans/2026-09-14-outer-admission-causal-binding.md`

## Implemented scope

1. The offline outer-admission adapter now checks a canonical commitment of the
   retained source `Plan` before any source gate; a substituted plan blocks.
2. It preserves source-order gates, source-style tracker-record failure
   handling, episode persistence, and the ephemeral active-reversal mapping
   visible to later producers within the same pass.
3. Its detached decision contains gate trace, safe entry-quality annotations
   (including whether a causal rejection tail was considered), and tracker
   identity only after an advisory registration. It contains no raw payload,
   fill, P&L, outcome label, broker action, or training readiness.
4. `ClosedBarCausalReplay` accepts an opt-in per-pass outer-input mapping.
   When supplied and activation is evidenced enabled, it requires one current,
   digest-matching `OUTER_ADMISSION_INPUT` event before watch/lifecycle state is
   touched, passes the private retained selected Plan to the adapter, and emits
   `ADMITTED_TRACKER`, `REJECTED`, or `BLOCKED` as an advisory replay outcome.
5. The old path with no outer-input mapping remains `OBSERVE_ONLY` by design.
   Checkpoint restore receives the same caller-supplied map and verifies it via
   bundle-bound digests as passes resume.

## Verification

- PASS (110):
  `python -B -m pytest tests/tree_replay/test_outer_admission_contracts.py tests/tree_replay/test_outer_admission_ports.py tests/tree_replay/test_outer_admission.py tests/tree_replay/test_causal_replay.py tests/tree_replay/test_causal_replay_checkpoint.py tests/tree_spec/test_outer_admission_source.py tests/tree_spec/test_causal_replay_source.py -q --tb=short -p no:cacheprovider`
- PASS: `python -B tools/check_causal_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`
  reported `VERIFIED`; both public readiness flags remain `false`.
- PASS: `git diff --check` over the changed implementation and focused tests.

## Still excluded

No live source import, filesystem/network/broker/Telegram call, delivery,
broker fill, economic simulation, dataset generation, model training, model
promotion, or live trading is enabled. Task 5 documentation and independent
review remain required before component acceptance.
