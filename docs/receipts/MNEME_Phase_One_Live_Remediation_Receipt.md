# MNEME Phase One live remediation receipt

Date: 2026-09-19  
Status: **READY FOR ONE FRESH AUTHORIZED LIVE RUN**

This receipt records the offline remediation after the three historical live
acceptance attempts. The historical attempts and their 18 consumed provider
calls remain preserved in `MNEME_Phase_One_Live_Acceptance_Blocker.md` and are
not reclassified as accepted gates.

DeepInfra access and the supplied credential were functional in those attempts.
The blocker was strict extraction/output acceptance and missing route evidence,
followed by incomplete P1.2/P1.3 execution. It was not provider availability.

The remediation:

- exposes the complete validator-owned concept and relationship vocabularies in
  the extraction prompt;
- requires raw JSON only, without fences, prose, comments, or invented enums;
- adds regression fixtures for every observed malformed or unsupported result;
- durably records naming requests/results, host/provider/model provenance,
  finish reason, nullable usage, and the identity-event relationship;
- accounts for every persisted extraction attempt and repair without
  double-counting, while preserving unknown usage as unknown;
- advances stores to schema 5 with explicit v4-to-v5 migration and preserves
  read-only historical checkpoint opening and private fork migration.

Offline validation completed before any new provider call:

- `.venv2/bin/pytest -q`: **196 passed**
- `.venv2/bin/ruff check .`: **passed**
- `.venv2/bin/mypy --strict src`: **passed**
- fresh isolated package install and CLI smoke: **passed**
- focused naming persistence and unknown-usage tests: **passed**
- observed malformed/unsupported extraction fixtures: **passed**

No new DeepInfra call was made by this remediation. One fresh predetermined
Phase One live run remains authorized separately, capped at 27 calls, with no
automatic resampling after a failed required result.
