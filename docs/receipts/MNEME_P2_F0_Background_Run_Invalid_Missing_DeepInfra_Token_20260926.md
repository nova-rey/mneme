# F0 background run — invalid missing credential environment

Date: 2026-09-26  
Run: `p23-f0-background-20260926`  
Disposition: `INVALID_PROVIDER_CONFIGURATION`

The extended F0 run was dispatched from commit `986133d`. The three local
DeBERTa qualification calls returned successfully. Before the first shared
Interloper developmental turn, the process had no inherited `DEEPINFRA_TOKEN`.
The request was persisted and marked `UNCERTAIN` with `HostError`; no Qwen
output, Gemma developmental response, extraction, assessment, learner update,
or readout was accepted from this run.

This is an execution-environment failure, not a scientific result. The raw
qualification and reservation artifacts remain under the preserved run root:

`/tmp/mneme-p23-f0-background-20260926/experiments/p2.3-f0-background-c-r-f0/revisions/2/runs/p23-f0-background-20260926/`

Historical F0, r6, and r7 evidence is unchanged. A fresh run root is required
for continuation after loading the already-authorized credential without
printing or persisting its value.
