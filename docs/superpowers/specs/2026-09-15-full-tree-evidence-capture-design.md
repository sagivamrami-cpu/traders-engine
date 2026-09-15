# Full-Tree Historical Evidence Capture Design

**Status:** approved for offline implementation; no external-data access is
authorized by this design.

**Authorization:** user instruction to continue autonomously on 2026-09-15.

**Depends on:** `docs/superpowers/specs/2026-09-15-full-tree-causal-provider-design.md`
and the pinned `TreeReader` / `TreeRevalidation` source components.

## Goal

Build a private, offline capture boundary that turns caller-supplied historical
raw responses at one decision time into a `FullTreeEvidenceBundle`. It must
discover the exact calls the complete source tree actually makes, preserve their
order and independent clock reads, and produce a bundle that the existing
`FullTreeCausalReplay` can rerun without a live loader.

The capture result is evidence for tree observation only. It is not a candidate
admission, fill, economic outcome, success/failure label, dataset row, model
prediction or live-trading permission.

## Why capture is necessary

The source tree decides which inputs it needs as it follows branches. A static
prebuilt list of frames, calendar files and reports would either omit required
calls or invent unavailable facts. Capture runs the actual local `TreeReader`
or `TreeRevalidation` once against a strictly supplied input source, recording
each requested raw port. The resulting immutable bundle is then independently
replayed through the existing causal provider.

```text
caller-supplied as-of values
        │
        ▼
CaptureInput ──> RecordingSource ──> actual TreeReader / TreeRevalidation
        │                                      │
        └──── availability + digest ───────────┘
                         │
                         ▼
             private FullTreeEvidenceBundle
                         │
                         ▼
               existing FullTreeCausalReplay
```

## Boundary and inputs

`FullTreeCaptureInput` is a caller-owned, in-memory port. It exposes one method
conceptually equivalent to:

```python
read(kind: str, arguments: Mapping[str, object], *, decision_time: datetime) -> CapturedValue
```

`CapturedValue` contains the private return value plus its `observed_at`,
`available_at`, `covered_through` and a SHA-256 `content_digest` provided by the
approved upstream historical adapter. Values use the existing artifact kinds:
`FRAME`, `CLOCK`, `TEXT`, `REPORT_LIST`, `BYTES`, `SHADOW_RESULT`, and `ERROR`.

The capture boundary validates that the requested port kind, arguments and
artifact kind are compatible with the full-tree contracts. It never provides a
default, retries through a different source, reads a filesystem path, opens a
network connection or manufactures a negative signal. A missing response,
invalid window or invalid digest blocks capture. A deliberately supplied
`ERROR` is recorded and raised at the exact source call, allowing the original
tree's own error handling to determine its observation path.

No vendor adapter is included in this work. Databento coverage, instrument
mapping, external calendar/options provenance and raw-data retention remain
separate approvals and contracts.

## Capture modes

The capture request contains `run_id`, exact `instrument`, `pass_id`, UTC
`decision_time`, `source_variant`, and one mode:

| Mode | Actual execution during capture | Produced pass |
| --- | --- | --- |
| `TREE_WALK` | `TreeReader.walk`, then `trade_from_walk` only when complete and directional | normal full-tree pass |
| `TREE_REVALIDATION` | `TreeRevalidation.revalidate_pending` on a private, digest-committed pending plan | revalidation pass |

Only `full_tree:house` and `full_tree:strict` are accepted. The capture source
does not accept a `Walk`, `Plan`, revalidation boolean, or final outcome from
the caller. It builds operations only by observing calls made by the actual
source implementation.

## Output and integrity

`FullTreeEvidenceCapture.capture(...)` returns a private result containing:

- the `FullTreeEvidenceBundle` with one strictly scheduled pass;
- a payload-free `FullTreeCaptureReceipt` with the bundle manifest digest,
  pass identity, operation count and source trace digest.

Each source request becomes a distinct artifact and operation, even when two
requests return the same raw value. This deliberately avoids unsafe deduping.
The receipt contains no frame, text, bytes, report content, pending plan or
tree result. A subsequent replay must be able to reproduce the receipt's trace
digest from the bundle; a mismatch is evidence of non-deterministic or altered
source behavior and must block verification.

Capture never serializes raw payloads into a manifest, checkpoint, receipt or
`agent-exchange`. The caller remains responsible for private raw-data storage.

## Error behavior

- An input response absent for a requested port raises `FullTreeCaptureError`
  before any synthetic artifact is made.
- A supplied value outside its availability interval is rejected before bundle
  construction.
- A scheduled source exception is represented by the existing `ERROR` artifact
  and is raised at that operation, not converted to a false result.
- A walk that stops early yields a valid bundle with only its reached operations.
  There is no expected suffix and no claim that unreached data was negative.
- A capture request may not reuse an existing `pass_id` in the same capture
  batch; batch construction retains the existing strict time ordering.

## Verification

Acceptance requires tests that prove:

1. actual house and strict captures produce replayable bundles and identical
   public trace commitments after replay;
2. repeated raw reads become distinct ordered operations;
3. a source-caught supplied error is scheduled rather than pre-resolved;
4. missing/late/mismatched caller values fail closed;
5. capture rejects caller attempts to supply final tree results;
6. receipt/manifest output has no raw value, source report or private pending
   plan; and
7. existing full-tree provider, replay, checkpoint and source-audit suites stay
   green.

Independent review remains required before accepting the capture component.

## Out of scope

- Databento or any other vendor client, file importer, storage policy or raw
  data download;
- source-to-vendor symbol translation;
- economics, fills, costs, TP1 labels, management policy, dataset generation,
  model fitting/evaluation or promotion;
- broker execution, deployment and live trading.
