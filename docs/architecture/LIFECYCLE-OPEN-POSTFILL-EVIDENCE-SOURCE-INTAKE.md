# Lifecycle OPEN post-fill evidence intake

Source: pinned `chartdesk/tracker.py::_check_live_locked`, lines 2647-2689.
For an OPEN record, initialize `(low, high)` from supplied spot. Fetch a
corrected 15-minute tape only through a supplied port; reject unverified or
`tv_stale` tape unless the accepted historical-safety predicate allows it.
Use the accepted fill locator; only then derive post-fill extrema with
`fill_bar_first=True`, combine them with spot, and observe minimum success.
Any unreadable/unsafe/unlocatable tape falls back to spot alone. This slice
does not resolve protection, targets, progress, state, outcomes, messages,
persistence, economics, labels, dataset or training.
