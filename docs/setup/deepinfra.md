# DeepInfra live qualification setup

This is the remaining external step for P0.1. No token belongs in the repository, shell
history, reports, fingerprints, or provenance.

1. Create or sign in to a [DeepInfra account](https://deepinfra.com/).
2. Create an API token in the account dashboard. Add a small credit balance if the account
   requires prepaid usage.
3. In the activated MNEME environment, export the token:

   ```bash
   export DEEPINFRA_TOKEN="..."
   ```

4. Check configuration without printing the token:

   ```bash
   mneme doctor
   mneme host inspect gemma-deepinfra
   ```

5. Run the bounded qualification:

   ```bash
   mneme host qualify gemma-deepinfra \
     --json artifacts/gemma-deepinfra.json \
     --report artifacts/gemma-deepinfra.txt
   ```

The JSON and text artifacts are written under `artifacts/`. A successful qualification
requires basic generation, fallback-hosted chat transport, three prompt-driven structured
JSON cases with schema validation, and no unexpected provider errors. Seed control and
native schema-constrained output are reported as unsupported unless a future backend
verifies them. The suite is intentionally small and bounded; do not treat it as a claim
that the Concept Residue Extractor is solved.

DeepInfra's official [OpenAI-compatible quickstart](https://github.com/deepinfra/docs/blob/main/quickstart.mdx)
documents bearer authentication and the base URL `https://api.deepinfra.com/v1/openai`.
The selected endpoint is `/chat/completions`, with model `google/gemma-4-E4B-it`.

As checked 2026-09-17, DeepInfra's public model catalog reported 131,072 context, $0.020
per 1M input tokens, and $0.100 per 1M output tokens for this model. Prices, availability,
limits, and account requirements can change; the live provider response is authoritative.

After qualification, remove the credential from the shell with:

```bash
unset DEEPINFRA_TOKEN
```
