# Lifecycle OPEN protection intake

Pinned source `tracker.py` lines 2690-2715 establishes protection first. From
the accepted post-fill `(low, high)` window derive the protective level. If
the window touches protection and an unhit target, order is unknowable: mark
terminal (`STOPPED` before any hit, otherwise `DONE`), use the accepted
ambiguous result/message, and write only its raw tracker fact. A future slice
will handle ordinary target/progress/protection order. No economic P&L or
model label is implied by this conservative lifecycle fact.
