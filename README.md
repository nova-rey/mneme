# MNEME

MNEME (Model Instance Development Through Earned Association) is a research system for
testing whether frozen model instances can develop persistent, experience-dependent
behavioral differences. It has not demonstrated individuality; this repository is the
narrow Phase 0.1 laboratory boundary.

## Install and test

```bash
python -m venv .venv && . .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check .
```

The inexpensive suite uses only `FakeHost`. Run `mneme host qualify fake --json
artifacts/fake.json --report artifacts/fake.txt` for a local qualification artifact.

## Hosts

`mneme doctor`, `mneme host list`, and `mneme host inspect fake` work without credentials.
For hosted Gemma through DeepInfra, export `DEEPINFRA_TOKEN` and run
`mneme host qualify gemma-deepinfra --json artifacts/gemma-deepinfra.json --report artifacts/gemma-deepinfra.txt`.
The hosted path is opt-in and is never part of ordinary CI. See [Gemma decision](docs/decisions/gemma.md).

## Project context and boundary

Supplied specifications and research are preserved under [docs/](docs/README.md). P0.1
implements provider-neutral request/result/fingerprint contracts, explicit capabilities,
deterministic FakeHost, Hugging Face and DeepInfra hosted Gemma boundaries, and qualification reporting.
It deliberately does not implement memory, associations, learning, identity evolution,
experiments, a database, a web UI, or neural intervention.

P0.2 adds the first durable state layer: per-lineage SQLite stores, immutable accepted
episodes, revisions, manifests, checkpoints, restart recovery, and independent forks.
It still does not implement learning, recall, associations, personality, or identity
development. The state CLI requires an explicit `--store PATH`; see the approved
[P0.2 plan](docs/Approved%20Plans/MNEME_P0.2_Durable_Lineage_History_Checkpoints_Plan.md).

P0.3 adds versioned experiment contracts, fixture split validation, domain-separated
random streams, host/budget preflight, immutable laboratory artifacts, and a frozen
FakeHost evaluation boundary. It does not execute the full P0.4 experiment runner or
implement developmental mechanisms; see the approved [P0.3 plan](docs/Approved%20Plans/MNEME_P0.3_Experiment_Contracts_Experimental_Isolation_Plan.md).

The host boundary keeps administrative MNEME metadata out of model-visible messages. Hosted
credentials are environment-only; qualification artifacts may contain provider metadata but
never secrets.

Gemma's structured-output qualification is prompt-driven JSON validation only. The hosted
backend does not advertise native structured-output capability, and its message rendering is
explicitly labeled `mneme_fallback_transcript_v1`.

See [DeepInfra setup](docs/setup/deepinfra.md) for the short live-qualification procedure.
