# MNEME P2.3 extraction v3 Markdown-list correction receipt

**Date:** 2026-09-24  
**Historical failure:** `p2-pilot-recovery-20260924h`, `extraction-s1-e1`  
**Disposition:** offline correction passed; live verification pending

The h continuation stopped after Gemma returned a rendered quotation for a
Markdown list item while omitting the immutable source's leading `* ` and
bold markers. Strict source-bound validation correctly rejected both the
initial result and its one repair.

The provider-facing extractor contract is now `residue-v3`. It retains the
strict quotation and enum rules and adds a concrete list/bold example stating
that a quotation must include the leading list marker and both `**` pairs.
The deterministic validator, canonical span representation, one-repair rule,
and historical residue-v1/v2 records are unchanged.

Regression coverage now checks that the rendered list text is rejected while
the exact bullet-and-bold quotation is accepted. The prompt contract test
asserts that the new instruction is serialized for provider use.

Offline validation: 321 pytest tests passed, Ruff passed, strict mypy passed
for 50 package files, and fresh wheel/install CLI smoke passed. No provider
call was made for this correction.

The next live action is one fresh private recovery coordinate for the h
failed extraction, using `residue-v3`, with no unchanged resampling. The h
receipt and all earlier historical evidence remain immutable.
