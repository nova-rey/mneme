# MNEME Phase Two Episodic Provenance Addendum

Date: 2026-09-26  
Status: additive implementation decision; historical Phase Two evidence remains immutable.

P2 developmental credit is now able to consume a bounded conversational arc
identity in addition to the existing accepted turn episode. A `ConversationTurn`
is an accepted message-level record. A `ConversationEpisode` is a deterministic
arc over one or more turns, with topic keys, ordered source roles, relationship
and outcome references, pivot/closure reason, and prior related arc IDs. The
existing P0.2 `episodes` table remains the immutable turn ledger; arcs are stored
beside it in `conversation_arcs`, `conversation_arc_members`, and
`conversation_arc_events`.

The tracker uses a one-turn tangent tolerance. A shared topic keeps an arc open;
one disjoint turn is held as a tangent; a second consecutive disjoint turn or an
explicit pivot closes the current arc. Re-entry metadata records the initiator
role and prior related arc. External/Qwen re-entry is eligible for ordinary
external handling. Model/Gemma re-entry inside the explicit two-round window is
recorded but receives no independent credit (`model_reentry_refractory`). A
model-origin recurrence after that window remains model-origin and is governed
by the existing bounded dependence rules. A response to a model-initiated
callback retains that ancestry; any new outcome evidence is preserved for the
existing consequence path and is not converted into a fresh independent root.

Learner edge state records accepted arc keys so repeated observations inside one
arc do not advance relevant opportunities or receive duplicate credit. Rows that
predate arc metadata remain readable with null/empty arc fields and are not
retroactively reinterpreted. Administrative arc IDs are audit keys only; they
are not generation inputs and do not alter route ranking.

The v6 cross-thread audit is intentionally inconclusive under this amended
model: its historical records predate arc/re-entry fields. The six admitted
observations remain current-input echoes with zero credit, all ten materialized
edge states remain support/accessibility zero, and no retroactive credit or
consolidation is awarded. See the [episodic provenance audit](../receipts/MNEME_P2.3_Cross_Thread_v6_Episodic_Provenance_Audit_20260926.md)
and its machine-readable companion.
