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

The host boundary keeps administrative MNEME metadata out of model-visible messages. Hosted
credentials are environment-only; qualification artifacts may contain provider metadata but
never secrets.

Gemma's structured-output qualification is prompt-driven JSON validation only. The hosted
backend does not advertise native structured-output capability, and its message rendering is
explicitly labeled `mneme_fallback_transcript_v1`.

See [DeepInfra setup](docs/setup/deepinfra.md) for the short live-qualification procedure.
