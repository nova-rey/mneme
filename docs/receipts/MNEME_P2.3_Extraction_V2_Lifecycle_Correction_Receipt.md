# MNEME P2.3 extraction v2 and lifecycle correction receipt

**Date:** 2026-09-24  
**Disposition:** offline correction passed; historical live evidence preserved; live recovery pending

The latest persisted pilot attempt `p2-pilot-recovery-20260924g` stopped at
`extraction-s0-e8` after its initial extraction and one permitted repair both
returned the non-verbatim quotation `consistent, focused effort paid off.` for
the immutable source text `**consistent, focused effort paid off**.`. Both
provider results were returned and persisted; strict quotation validation
correctly rejected them. No historical artifact was rewritten.

The correction makes the stricter provider-facing extraction contract
`residue-v2` the default for new extraction calls, including current-run
repairs and explicit recovery operations. The residue schema and strict
source-slot quotation validator are unchanged. The prompt now gives an exact
character-preserving Markdown example and directs the model to omit an
assertion when it cannot copy a quotation exactly.

The pilot lifecycle now records execution status in the run manifest as well
as the pilot ledger, keeps the nested pilot status synchronized on terminal
and paused transitions, persists accepted-development coordinates before
extraction begins, and persists the repair count before dispatching the one
permitted repair. A restart can therefore distinguish an accepted response
from a fully completed developmental coordinate without redispatching the
response.

Contradicted semantic observations retain their approved no-credit behavior,
but their learner update reason is now `contradicted_no_positive_credit` rather
than a cap-exhaustion label. The approved plan's Q3 wording now states the
prospective `present` / `contradicted` / `negated` representation.

## Offline validation

- focused extraction, lifecycle, learner, publication, and pilot tests: passed;
- complete pytest suite: **320 passed**;
- Ruff: **passed**;
- strict mypy: **passed** (`50` source files);
- wheel/fresh-install smoke: **passed** from the current working tree;
- provider calls for this correction: **0**.

The next live action is a new private continuation copied from the preserved
`g` stores. It may reuse the accepted `e8` response, create one new recovery
interpretation operation under `residue-v2`, and use at most its one permitted
repair. The failed operation and all prior receipts remain immutable.
