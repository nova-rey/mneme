# MNEME P2.3 Assessor Qualification Failure Receipt

**Status:** FAILED — PILOT NOT STARTED
**Date:** 2026-09-20
**Qualification run:** `qualification-20260920`
**Scientific contract:** `p2-developmental-pilot / contract_revision 1`

This receipt records the one fixed three-call qualification attempt. The
provider and credential were functional. All three calls returned provider
responses and usage. Qualification failed because the returned text did not
match the production assessor JSON contract. No repair, retry, prompt change,
replacement call, or pilot call was made.

## Call accounting

| Call | Case | Provider response | Durable result | Structural validation | Semantic qualification | Usage | Disposition |
|---|---|---|---|---|---|---|---|
| `assessor-q1` | Q1 | returned | persisted before validation | failed: newline-delimited objects, no top-level `assessments` array; unsupported `satisfied`/`not_satisfied`/`none` values | not attempted | 502 input / 125 output / 627 total | rejected |
| `assessor-q2` | Q2 | returned | persisted before validation | failed: newline-delimited objects, no top-level `assessments` array; unsupported relation/status/dependence values | not attempted | 539 input / 78 output / 617 total | rejected |
| `assessor-q3` | Q3 | returned | persisted before validation | failed: newline-delimited objects, no top-level `assessments` array; unsupported `false` values | not attempted | 409 input / 76 output / 485 total | rejected |

Totals: **3 DeepInfra calls**, **1,450 input tokens**, **279 output tokens**,
**1,729 total tokens**. The provider did not supply a cost field; using the
recorded setup price references would only be an estimate (approximately
`$0.000057`), not an actual charge.

## Sanitized returned text

The following is the complete returned text for each small qualification case;
it contains no credentials or authorization metadata.

### Q1

```text
{"monitor_id": "latch", "status": "satisfied", "relation_support": "satisfied", "expression_status": "satisfied", "dependence": "none"}
{"monitor_id": "echo", "status": "not_satisfied", "relation_support": "not_satisfied", "expression_status": "not_satisfied", "dependence": "none"}
{"monitor_id": "unrelated", "status": "not_satisfied", "relation_support": "not_satisfied", "expression_status": "not_satisfied", "dependence": "none"}
```

### Q2

```text
{"monitor_id": "jacket_direction", "status": "satisfied", "relation_support": "raises", "expression_status": "satisfied", "dependence": "none"}
{"monitor_id": "shade", "status": "satisfied", "relation_support": "raises", "expression_status": "satisfied", "dependence": "replay_linked"}
```

### Q3

```text
{"monitor_id": "dial", "status": "false", "relation_support": "false", "expression_status": "false", "dependence": "none"}
{"monitor_id": "unavailable_output", "status": "false", "relation_support": "false", "expression_status": "false", "dependence": "none"}
```

## Disposition

The qualification gate is **FAIL**. The three results remain in the private
ignored laboratory artifact tree for audit. The proposed 299-call pilot ceiling
is untouched, and P2.3 must not proceed to pilot execution without a separately
reviewed correction and fresh authorization.
