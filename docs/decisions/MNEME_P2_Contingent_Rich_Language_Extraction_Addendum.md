# MNEME P2 contingent rich-language extraction addendum

Date: 2026-09-24  
Status: active prospective correction; historical turns and artifacts remain immutable  
Extractor contract: `residue-v5`  
Interloper policy: revision 2

## Decision

The preserved interactive transcript shows genuine response-contingency and
increasingly poetic/reflective language in turns 4–8. The acquisition boundary
must extract only source-grounded material that fits the existing residue
ontology. It is not required to encode every sentence or literalize metaphor.

The `residue-v5` prompt therefore tells the extractor to return concise,
high-confidence candidate records; ignore decorative metaphor and unsupported
implication; admit abstract associations only when the existing ontology can
represent them; and return fewer candidates or `{}` when no trustworthy item is
available. Exact quotation resolution, item-wise admission, capacity bounds,
normalization, and fail-closed provenance remain unchanged.

Item-level normalization continues to preserve valid concrete material when a
separate candidate is malformed or uses an unsupported relation. Rejected or
abstained items remain in the durable normalization report for audit. No new
relationship vocabulary, fuzzy matching, parser, or learner rule is introduced.

The Interloper prompt is amended prospectively with policy revision 2. It keeps
contingent response behavior but asks the participant to maintain an independent
agenda and voice, avoid repeatedly mirroring or intensifying poetic framing,
and return naturally to practical complications, grounded questions,
disagreement, or forward topic movement. Humor, emotion, metaphor, callbacks,
and natural topic drift remain allowed.

Turns 0–8 are historical evidence and are not rewritten or regenerated.

