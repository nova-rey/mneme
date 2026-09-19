# MNEME Phase One fresh live acceptance failure receipt

Date: 2026-09-19  
Remediation base: `0f8bdfe539665503df0456275b521b463b80e8ab`  
Status: **BLOCKED — stopped at P1.1 after the permitted repair**

This is one newly authorized fresh run. The three historical attempts and their
18 calls remain unchanged and are not reclassified. The credential and
DeepInfra transport were functional: all four new calls returned a provider
response from `google/gemma-4-E4B-it`.

The run executed the two predetermined P1.1 responses, then the first P1.1
interpretation and its one permitted repair. Both extraction results were
durably persisted, but both failed the same strict source-span validation:

`residue.core_concepts[1].source_spans[0]: span must satisfy 0 <= start < end <= source length`

The required P1.1 interpretation therefore did not publish. The run stopped
without attempting another sample. P1.1 route evidence was not established;
P1.2 and P1.3 received zero calls.

New-call accounting:

| Gate | Role | Calls | Input tokens | Output tokens | Total tokens | Result |
|---|---|---:|---:|---:|---:|---|
| P1.1 | responses | 2 | 33 | 384 | 417 | provider responses accepted as episodes |
| P1.1 | extraction initial | 1 | 661 | 199 | 860 | persisted, source-span validation failed |
| P1.1 | extraction repair | 1 | 696 | 201 | 897 | persisted, same validation failure |
| **Total** |  | **4** | **1,390** | **784** | **2,174** | **P1.1 failed; run stopped** |

The provider reported `finish_reason=length` for the two bounded response calls
and `finish_reason=stop` for both extraction calls. No cost basis was available.
No P1.2 identity, response, extraction, or frozen-probe call occurred. No P1.3
comparison call occurred. No Phase One release tag or closure was created.

This failure is classified as model-output/validation failure at the strict
source-span boundary. The implementation correction was exercised; the
scientific acceptance criteria were not weakened and no further live budget is
authorized by this run.
