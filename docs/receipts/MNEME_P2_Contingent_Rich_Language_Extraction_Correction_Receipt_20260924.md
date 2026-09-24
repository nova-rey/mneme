# MNEME P2 contingent rich-language extraction correction receipt

Date: 2026-09-24  
Run preserved: `contingent-live-20260924`  

## Evidence

The sanitized transcript at
`MNEME_P2_Contingent_Conversation_Transcript_20260924.md` preserves turns 0–8
and shows Qwen responding to Gemma while increasingly amplifying poetic and
philosophical framing. Those turns remain unchanged research evidence.

## Offline correction

- Prospective extractor contract advanced from `residue-v4` to `residue-v5`.
- The model-facing prompt now requests only concise, high-confidence,
  source-grounded candidates; it explicitly allows abstention and `{}` for
  unrepresentable metaphor, and asks for item-wise extraction rather than a
  commentary-bearing explanation of every source sentence.
- Exact quotation provenance, deterministic offsets, item-wise admission,
  capacity handling, and strict validation remain unchanged.
- Interloper policy revision 2 asks for contingent but independently voiced
  responses and discourages repeated mirroring or poetic escalation without
  making the participant a scripted interviewer.

## Regression coverage

Fixtures cover an empty residue for pure metaphor, mixed literal/figurative
material retaining a supported edge while rejecting an unsupported literalized
edge, and an abstract but source-supported association. Existing malformed,
capacity, provenance, and historical provider-output fixtures remain active.

Focused tests: 82 passed. Full pytest: 389 passed; Ruff passed; strict mypy
passed; wheel build and fresh-install import smoke passed. CI is required
before any live continuation.

## Live boundary

No provider call was made for this correction. The preserved conversation is
not restarted; turns 0–8 remain immutable. Continuation remains subject to the
existing interpretation-quality stop rule and transcript publication at every
boundary.
