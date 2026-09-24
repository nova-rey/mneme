# MNEME P2 contingent accepted-recovery resume correction

Date: 2026-09-24

The first resumed invocation after `residue-admission-v1` found that the original extraction operation could be revisited even though its evidence-review recovery had already been accepted. Reusing the original operation led to a stale-manifest publication attempt. The runtime now detects a durable accepted/result-ready `-evidence-review` recovery and returns that validated recovery directly, without another provider call or a second publication.

This is an idempotent resume correction. It does not rewrite the original extraction, recovery, episode, graph, or learner records. The two failed no-provider resume invocations and all 47 historical provider calls remain preserved.

Offline validation: 380 pytest tests, Ruff, strict mypy, wheel build, fresh-install smoke, and CI required after this commit.

The subsequent audit found and corrected one representation-only issue in the
new admission layer: auxiliary records are now checked without replacing raw
quotation evidence with internal spans before strict validation. No provider
call was made for that correction.
