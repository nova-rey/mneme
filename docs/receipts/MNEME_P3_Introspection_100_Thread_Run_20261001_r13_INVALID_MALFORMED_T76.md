# r13 invalid continuation attempt

r13 restarted from the compact immutable Thread-75 state and completed the
Thread-76 conversation. Its first introspection review returned a bounded
zero-effect/INSUFFICIENT JSON object, but used the arc ID rather than one of
the two supplied target aliases. The repair repeated that same no-op shape.
Because the alias was invalid, r13 stopped before accepting any adjustment;
it is not a behavioral result. The complete attempt is in the adjacent
`r13_INVALID_MALFORMED_T76.tar.zst` archive (SHA-256
`8dae27be89a6328ab7b1a1aca72a214dcdf57a97c2df616ef5edc69d771b8c08`).

The correction recognizes only an explicit zero-effect, zero-confidence,
INSUFFICIENT no-op as a valid abstention, without accepting an invalid target
or creating credit. The next attempt restarts from compact checkpoint 75.
