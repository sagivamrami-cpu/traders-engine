# Task 3 final independent re-review

Status: CHANGES_REQUESTED

## Scope and method

Reviewed the Task 3 section of `docs/superpowers/plans/2026-09-15-closed-bar-causal-replay.md`, the checkpoint design in `docs/superpowers/specs/2026-09-15-closed-bar-causal-replay-design.md`, all prior Task 3 reports/reviews in this SDD directory, and the current Task 3 implementation/tests:

- `trading_system/tree_replay/causal_replay_checkpoint.py`
- `trading_system/tree_replay/admission_context.py`
- `trading_system/tree_replay/clock.py`
- `tests/tree_replay/test_causal_replay_checkpoint.py`
- `tests/tree_replay/test_admission_context.py`
- `tests/tree_replay/test_shared_clock.py`

Per the request, this was a static independent review. I did not import or execute retained source, run the project test suite, edit implementation/tests, use subagents, or commit.

## Prior findings

- **Ledger/bundle anchor binding: closed.** `checkpoint_from()` and `restore_checkpoint()` both call `_validate_ledger_prefix()` (`causal_replay_checkpoint.py:140, 176`). That validator requires each consumed record's indexed `pass_id`, `decision_time`, and full ordered event prefix to equal the immutable bundle (`:227-234`). Creation and checksum-recomputed restore regressions are at `test_causal_replay_checkpoint.py:98-127`.
- **Forged provider source/future schedule substitution: closed for identity and suffix substitution.** A caller-retained `ReplayProviderBaseline` is required at checkpoint creation/restore (`causal_replay_checkpoint.py:43-102, 135-138, 165-189`), and recomputed-checksum watch-source, publication/lock substitution, and publication-addition regressions are at `test_causal_replay_checkpoint.py:130-165`.
- **Distinct shared-clock instances: closed.** Creation rejects `watch.source._clock is not admission._clock` (`causal_replay_checkpoint.py:137-138`); the time-equal, distinct-instance negative case is at `test_causal_replay_checkpoint.py:168-178`.
- **I1, over-six-digit ISO fractions: closed.** Both deserializers now use the same date/time-shape guard, accepting both extended and basic ISO forms and rejecting a fractional group longer than six digits before `datetime.fromisoformat()` (`causal_replay_checkpoint.py:255-264`; `admission_context.py:463-472`).

### Required I1 probes

The source canonical digest is SHA-256 of sorted, compact UTF-8 JSON (`causal_replay_contracts.py:74-84`). I independently recomputed checksums over four minimal JSON-shaped probe values using that same documented canonical encoding; all four timestamps match the current guards with a seven-digit fraction and therefore take the `microsecond-exact` rejection branch.

| Surface | ISO form | Timestamp | Recomputed SHA-256 | Static result |
| --- | --- | --- | --- | --- |
| Outer checkpoint | extended | `2026-09-09T16:01:00.1234567+00:00` | `bd8e922e4dcefb5de9cfff77ad61008b0a4f7ebc3083278731b74acd8725db65` | reject |
| Outer checkpoint | basic | `20260909T160100.0000000+0000` | `b4438879c77c9f138a4076126723a50bd74134c7ed0fbe0a76e754760fb25dbc` | reject |
| Packed snapshot | extended | `2026-09-09T16:05:00.1234567+00:00` | `55d387f27fd85ac34755ce4affbc4fbeca2cb66654e775c074696209dc52a838` | reject |
| Packed snapshot | basic | `20260909T160500.0000000+0000` | `e94b76fd37e4b28e1ab66848bac6ec1ce7be159a5ec660790786eefbfde276d7` | reject |

The retained regression tests also recompute the actual enclosing digest before restore: outer extended/basic at `test_causal_replay_checkpoint.py:181-194` via `_rehash_checkpoint()` (`:218-220`), and packed extended/basic at `test_admission_context.py:365-384` via `canonical_digest(snapshot["state"])`. Thus I1 is not masked by a stale checksum.

## Finding

### Important I2 — baseline matching permits a clock backdate before an already-consumed publication

`ReplayProviderBaseline._matches_checkpoint()` derives how many publications have been consumed exclusively from the length/equality of the remaining suffix (`causal_replay_checkpoint.py:76-96, 218-224`). It then reconstructs the expected current provider seed from that consumed prefix. It never requires every omitted/consumed publication's `available_at` to be no later than `snapshot.state.decision_time`, nor does it bind the checkpoint time to the consumed schedule boundary.

`CausalAdmissionContext.from_replay_snapshot()` only rejects a *remaining* publication whose availability is at or before the supplied time (`admission_context.py:369-388`, especially `:381-384`). It cannot see an omitted, already-consumed publication. Its provider constructors validate a seed's internal `observed_at <= available_at <= covered_through` relation, but do not require a restored provider seed's `available_at` to be no later than the restored decision time (`tracker_storage.py:27-33, 148-155`; `admission_io.py:57-84`).

Consequently, for a checkpoint taken after a publication at `P` has been consumed, an adversary can retain the exact empty/correct remaining suffix and the expected post-publication provider image, set the outer `clock_time`, admission snapshot `decision_time`, and watch `observed_at`/`available_at` to an earlier `T < P`, recompute the nested admission checksum and outer checkpoint checksum, and supply `ReplayClock(T)`. The current comparisons pass: the baseline expects the post-publication image from the omitted prefix, no remaining publication is at/before `T`, and the watch/admission clocks agree at `T`. The resulting provider image is causally from the future of the restored clock.

This conflicts with the design's one-clock rule that publications at or before each anchor are applied before building providers (`closed-bar-causal-replay-design.md:153-156`) and its requirement that future publications cannot affect an earlier pass (`:233`). It also means the former baseline protection is incomplete: source/suffix substitution is rejected, but checkpoint chronology is not.

Required correction: when matching a snapshot to the trusted baseline, derive the consumed publication and lock prefixes and reject unless every consumed publication is `available_at <= decision_time` and every consumed lock step is complete at or before that time. Add a checksum-recomputed regression that consumes a future scheduled publication, backdates all outer/admission/watch clock fields before it, rehashes both images, and asserts restore fails. Keep the existing identity/suffix checks.

## Scope check

The I1 correction is confined in the reviewed implementation to the two timestamp guards and the two authorized checkpoint/admission-context regressions; it adds no runner, retained-source access, delivery, economic, dataset, training, model, live-trading, or readiness-positive path. The relevant Task 3 paths are untracked in this shared dirty worktree, so Git cannot provide a historical line diff for those additions; this conclusion is from current-path inspection and the correction report, not a claim of a clean worktree.

## Verification evidence

- Static guard/checksum probes above: all four seven-digit fractional forms route to rejection.
- Static source/test inspection: all prior Task 3 findings have the listed code paths and adversarial regressions.
- Project tests were intentionally not run because the review request forbids executing retained source. The prior correction report's `183 passed in 17.39s` is historical evidence only and was not treated as fresh verification.

No source/test change was made by this review.
