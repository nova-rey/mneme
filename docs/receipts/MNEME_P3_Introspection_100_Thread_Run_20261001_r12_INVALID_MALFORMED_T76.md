# r12 invalid continuation attempt

The compact-storage continuation was started from the verified Thread-75
state and reached Thread 76. It stopped before advancing the study when the
first no-exposure arc review returned an invalid target alias in both the
reflection and one bounded formatting repair. This is an instrumentation
failure, not a scientific result. The complete request/result, Thread-76
conversation, and compact subject stores are preserved in the adjacent
`r12_INVALID_MALFORMED_T76.tar.zst` archive (SHA-256
`1a85b6c7d5ce3fa48924ccd087ca0db0849c04ef24398e33cfac74f2dd6eb07f`).

The cause was deterministic: an arc with no recorded exposure was given a
synthetic target alias ending in `-none`, while Gemma returned the arc ID
without that suffix. The correction is to emit a valid no-target abstention
without a model review call. No Thread 1–75 state or historical receipt was
changed, and the next prospective run will restart from compact checkpoint 75.
