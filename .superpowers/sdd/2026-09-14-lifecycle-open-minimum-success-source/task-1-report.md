# Task 1 report — Lifecycle OPEN minimum-success source runtime

Status: IMPLEMENTED_AWAITING_CODEX_REVIEW

## Scope completed

- Added the private supplied-evidence runtime:
  `trading_system/tree_replay/_vendor/lifecycle_open_minimum_success.py`.
- Added focused behavioral coverage:
  `tests/tree_replay/test_lifecycle_open_minimum_success.py`.
- Added the private/offline usage boundary:
  `docs/architecture/LIFECYCLE-OPEN-MINIMUM-SUCCESS-SOURCE-USAGE.md`.

`LifecycleOpenMinimumSuccess.resolve(...)` uses only the accepted
`DeskSuccess`, `LifecycleTransitions`, and `LifecycleOutcomeShelf` helpers and
the supplied source clock. It preserves the retained source order: protective
touch; exact fresh quote gate only when no bar minimum exists; directional
progress-step update only while protection is untouched; source minimum points;
one message; and one raw `minimum_success` fact.

The runtime does not acquire quotes/bars, import or execute retained source,
resolve ambiguity/targets/protection, persist tracker state, deliver, or add
economic/replay/dataset/training/model behavior. The focused source port fails
the test immediately if acquisition, persistence, or delivery is attempted.

## TDD evidence

RED, before the runtime module existed:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py
10 failed in 0.20s
AssertionError: OPEN minimum-success module missing
```

GREEN after the minimal source-ordered projection:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py
10 passed in 0.47s
```

Final targeted dependency verification:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py
94 passed in 0.58s
```

Focused cases cover bar minimum fact/message behavior, protection-gated
progress, long-high and short-low progress inputs, exact fresh post-fill quote
eligibility, stale/wrong-lp/bar-extremes/protective/pre-fill quote rejection,
no-op immutability, and exactly one raw `minimum_success` result per success.

`git diff --check` reported no whitespace errors in this scope. Its only output
was line-ending warnings for pre-existing modified `AGENTS.md` and `README.md`.

## Scope concerns

Task 2's retained-source audit, explicit-root CLI, mutation/audit tests, and
readiness report are intentionally not implemented. The private raw tracker
fact remains neither an economic label nor any replay, dataset, training,
model, trading, or readiness artifact. No commit, push, unrelated-file edit,
or subagent work occurred.

## Fix round — source append-before-outcome ordering

Confirmed against retained `chartdesk/tracker.py::_check_live_locked` lines
2690–2704: line 2702 appends the minimum message before line 2703 writes the
raw `minimum_success` outcome. The runtime had written the outcome before
constructing its returned message list, making the local order drift despite
unchanged externally observable results.

Added one AST regression to
`tests/tree_replay/test_lifecycle_open_minimum_success.py`. It requires
`resolve` to construct its one-message `messages` list before calling
`self.outcomes._outcome`.

RED before the runtime change:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py -k 'constructs_message_list_before_writing_raw_minimum_outcome'
1 failed, 10 deselected in 0.59s
AssertionError: resolve must construct its one-message list
```

Minimal runtime change: construct `messages = [(minimum_message,
trade["to_group"])]` immediately before the existing raw outcome call, then
return that variable. No API or behavior was otherwise changed.

GREEN focused:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py
11 passed in 0.44s
```

GREEN dependent suite:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py
95 passed in 0.68s
```

## Fix round 1 — bar minimum takes precedence over an eligible quote

Added the behavior-level regression
`test_existing_bar_minimum_suppresses_an_otherwise_eligible_quote` to
`tests/tree_replay/test_lifecycle_open_minimum_success.py`. It supplies
`minimum_message="bar-minimum"` together with an otherwise eligible quote:
matching `lp`, fresh source time, post-fill timestamp, no forming-bar
extremes, and no protective touch. The test proves that the returned message
and minimum remain `bar-minimum`, no `exact_venue_quote` proof is created or
replaced, exactly one raw `minimum_success` fact is written, and the only
source-clock call is the accepted raw-fact write
(`outcomes_mkdir`, `now_epoch`, `open_outcomes`).

Mutation RED used the exact guard defect: temporarily remove
`not minimum_message and` from the quote gate. The new regression failed:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py -k 'existing_bar_minimum_suppresses_an_otherwise_eligible_quote'
1 failed, 11 deselected in 0.58s
AssertionError: returned quote-generated message did not equal bar-minimum
```

The guard was restored byte-for-byte; no production behavior change was
needed. GREEN focused and helper-dependent verification:

```text
python -m pytest -q tests/tree_replay/test_lifecycle_open_minimum_success.py tests/tree_replay/test_desk_success.py tests/tree_replay/test_lifecycle_transitions.py tests/tree_replay/test_lifecycle_outcome_shelf.py
96 passed in 0.60s
```
