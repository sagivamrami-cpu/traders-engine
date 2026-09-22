# Task1 runtime report

Status: DONE, awaiting independent task review.
Base/head c1b6071633c55376c64f0a98ece843706f420f49; no commits. Threefulladditions:
_vendor/lifecycle_identity.py, tests/tree_replay/test_lifecycle_identity.py,
docs/architecture/LIFECYCLE-IDENTITY-SOURCE-USAGE.md.

Original functions projected inertly from pinned tracker/trade_threads via AST;
six pure matching helpers, HEAD/identity, two receipt methods and threadcontext.
Only exact raw-port/call substitutions, four cacheName sites and inert constructor
added. Actual basis canonicalization and tracker geometry hashing reused.
No original source imported/executed. Existing runtime modules unchanged.

RED: python -B -m pytest tests/tree_replay/test_lifecycle_identity.py -q --tb=line -p no:cacheprovider
47failed0.83s exit1, all normalmissingmodule assertions (26dea0), before code.
GREEN: python -B -m pytest tests/tree_replay/test_lifecycle_identity.py tests/tree_replay/test_tracker_admission.py -q --tb=short -p no:cacheprovider
153passed2.13s exit0, pristine (fd897e);47newcases plus existing106.

Tests use literal geometry and independently precomputed SHA256 IDs (literal
JSON/SHA256, no implementation helper), rawJSONL/stats/queuecontent, actual
matching and context. Cover all source priority branches, ambiguity, state and
side, decimals/tolerances, lateheadline, contextload/clock, deliveryslack,
geometry/styles/legacydone-root/error paths, mtime0/change/nochange/errors and
separate readercache instances. Future receipt example deliberately passes raw
source: causal provider is still required, not a new source upperbound gate.
No provider-final receipt/context/verifier supplied. Raw ports have no writes.

Self-review: process cache owned by reader, original error boundaries retained,
one actual matcher shared by context. Source wrong migration ->dict annotation
retained; return is actual list. Usage explicitly pending audit/final acceptance.
No new policies, external IO, data/model labels or live actions. NextTask2source
proof+CLI, then fullgate/persistence/resolver/provider work remains.

I1 fix round1: reviewer identified missing explicit same-entry stop disambiguation
proof. Added one literal test with common entry110 and stops99.7/98, asserting
the first original object from text110.00/99.70 and no ambiguity. Source runtime
unchanged. Covering planned command above passed154cases2.29s exit0 (d39750),
pristine. Saved stop-disambiguation-probe.py actualsame testPASS/local disabled
stopbranch mutantFAIL verified442809exit0. Test file now48cases. Scopedfixdiff
task-1-fix-review.diff records the addition; independent rereview requested.
