# Shared clock task1 report

Plan2026-09-09-causal-admission-context, Task1 only. Existing approved C design;
full5file working package attached (two prior untracked artifact wrappers modified,
three new files). Original source projections unchanged. Main inline critical path.
Base=HEADc1b6071633c55376c64f0a98ece843706f420f49, dirty feature checkout preserved.

ReplayClock uses accepted UTC validation, monotonic advance and read-only now.
Optional exact clock binding requires equality with declared initial decision_time.
Artifact backend decision_time reads clock.now dynamically. State/effects and
chunk storage survive; standalone defaults unchanged; log.advance retains its
coverage guard then changes shared clock. Direct shared time advance is independent
of data availability, whose guards still run on actual reads/writes/snapshots.

Baseline109passed0.95s; new20tests normalRED missingclock, then combined170passed
2.79s covering state/quotes/logs/admissionframes. Source storageaudit2/watchaudit4
freshVERIFIED/no blockers/false readiness. No source thresholds changed.
Hashes: clock69990180d058e687c0cef84126bedc9e8d71e19c733b1072d61021d7c1c9c433;
storage de9c0e626d3260cca83edbe21e2a236dfb397fcd3d082ca36f6ca725f3644adc;
IO8d42227b2518c9dc9f3c7cd7327ff5786b730e19c3baaf79d61037eeef9da668.

Self-review: clock validates before mutation; constructor validates even future
artifact contexts structurally. Quote420->422actual consumer proves age uses new
clock. New state snapshot atT+2 does not lose stored rows/effects. Literal log
bytes/session and oldreader prefix tested. Backwards/naive/ns/string/None, exact
clock/subclass/time binding, expiry and delayed publication failures covered.
No wallclock/IO/sleep, full scheduler/loop, checkpoint, dataset/model or live action.
Main prepares Task2 tests in separate files while Task1 is reviewed.
