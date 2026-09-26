# MNEME P2.3 Shared-Interloper Local-Assessor No-Treatment Stop

Date: 2026-09-26  
Status: **INVALID — NO TREATMENT**  
Run: `p23-shared-interloper-ab-20260926-r6`

This is the first prospective shared-Interloper run using the qualified local
semantic assessor. It is a preserved invalid execution, not a behavioral A/B
result. Historical r3 provider-rate-limit, r4 control-permission, and r5
no-treatment receipts remain unchanged.

## Assessor qualification and execution

The pinned CPU specialist `cross-encoder/nli-deberta-v3-xsmall` passed the
production-shaped Q1/Q2/Q3 qualification and the held-out semantic set before
this run. The same local assessor was used for every dispatched assessment;
there was no Qwen assessor fallback. The shared Interloper remained the
previously qualified `Qwen/Qwen3-30B-A3B`.

The run completed its pre-treatment sanity check and all nine frozen
development coordinates without null responses or provider-rate-limit stops.
Gemma development, GLiNER extraction, local assessment, persistence, and the
shared Qwen turns all returned and were durably recorded. The run stopped at
the mandatory treatment-exposure gate; no readout, behavioral comparison, or
evaluation call was dispatched.

## Gate evidence

| Gate field | Persisted value |
|---|---:|
| M eligible state observed | `true` |
| M selected influence at any coordinate | `false` |
| M applied influence at any coordinate | `false` |
| C influence | `0` throughout |
| Treatment gate | `INVALID_NO_TREATMENT` |

Every exposure record `A:0` through `C:2` has `selected_count=0` and
`applied_count=0`. `A:0` correctly has no prior graph state; later coordinates
have eligible state where a graph snapshot exists, but no route was selected.

The local assessor did produce meaningful state. At `development-M-A-t0`, the
source-supported model-output relationship
`Drip Irrigation → causes → Slow Leak` was assessed as supported and admitted.
Its canonical binding is
`edge:66571a2fb4f35a3ba9656a34c66279d25b5ed5e1087c841928c2b9420d358136`.
The learner snapshot records accessibility `20000`, support `5000`, and
lifetime credit `20000` for that edge. This proves state formation; it does
not prove treatment exposure.

At `A:2`, the considered routes were the distinct `sponge method → causes →
mold` and `wicking idea → related → mold` routes. The admitted
`Drip Irrigation → causes → Slow Leak` edge was not query-matched by the
frozen input's wording (`drip method`), and no later B/C input supplied a
matching route. No code path selected or serialized MNEME influence. The
records therefore identify an experimental-condition/route-eligibility
mismatch, not a local-assessor failure.

## Accounting

Forty-four reservations were persisted: 18 local Gemma development calls, 9
local GLiNER extraction calls, 8 local NLI assessment calls, 3 local NLI
qualification calls, and 6 DeepInfra Qwen Interloper calls. DeepInfra usage
was 4,487 input, 244 output, and 4,731 total tokens. Local-call token usage is
not reported by the runtimes. No readout or evaluation calls occurred after
the gate.

The immutable run artifact manifest contains 68 artifacts and has SHA-256
`b88ffd5fad5cc8196366231efa823ab03a9c9f8d34c4089b6caae480e5883989`.

## Disposition

No behavioral result is assigned. This run cannot be called negative or
inconclusive because the treatment was never administered. Correct completion
would require a separately justified change to the frozen environmental
opportunity/route matching or to route-selection semantics, followed by a
fresh prospective run. Re-running this unchanged schedule would not repair the
condition and is not evidence.
