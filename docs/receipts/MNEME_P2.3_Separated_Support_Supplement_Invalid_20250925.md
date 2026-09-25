# P2.3 separated-support adequacy supplement — invalid dispatch

Status: **INVALID**  
Scientific identity: `p2.3-separated-support-adequacy / contract revision 1`  
Run: `p23-adequacy-balcony-v1-20260925`

The fixed run was dispatched once after the pushed offline preflight and CI
gate. Its first and only provider request was the predetermined Interloper
fit-check coordinate `interloper-fit-t00`. DeepInfra returned HTTP 429 (Too
Many Requests) before a model result was available. The durable reservation is
`UNCERTAIN`; no retry or replacement request was made.

No Gemma developmental response, extraction, assessment, learner publication,
or consolidation opportunity was dispatched. Therefore this run provides no
scientific result for the separated-support mechanism. It is an invalid
provider-transport attempt, not a negative consolidation result.

The exact sanitized request/result and reservation are retained in the private
lab artifact at `/tmp/mneme-p23-adequacy-20260925` and the run's
`receipts/p23-supplement-terminal.json`. Credentials and authorization
headers are not included. The historical P2.3 `COMPLETED_INADEQUATE` run and
all earlier evidence remain unchanged.
