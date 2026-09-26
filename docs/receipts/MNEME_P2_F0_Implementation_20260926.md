# MNEME Phase Two F0 implementation receipt

Status: `OFFLINE_VALIDATED_LIVE_PENDING`

This receipt records the first inspectable graph-pressure approximation for the
Associative Deformation Field experiment. The existing discrete route-note
backend remains `R` and was not rewritten. `C` remains the no-influence control.
The new controller policy is `selection_policy="field-v0"` and is versioned as
`f0-graph-pressure-v1`.

The implementation derives active concepts with deterministic conservative token
normalization, propagates pressure through accepted directed graph edges, and
uses the learner's persisted accessibility/support values. Pressure is bounded
by maximum depth 2, attenuation `0.6` per hop, minimum pressure `0.02`, total
fixed-point budget `1.0`, and four contributors. Quarantined or gated edges are
retained in the audit trace with zero applied pressure. Negative consequence
state can reduce earned strength but never creates positive pressure.

The text-mediated payload is capped at 900 characters and contains optional
conceptual framings. It does not expose provenance, learner scores, graph IDs,
experiment labels, or sibling information. The complete field trace is stored
in the controller turn trace query record, separately from the host-visible
payload. Optional stochastic exploration is not enabled in this version; all
results are deterministic and replayable.

Offline evidence:

- direct neighbor activation and conservative paraphrase reachability;
- attenuated bounded multi-hop propagation;
- multiple contributors under a hard budget;
- unrelated context and quarantine suppression;
- corrective consequence restraint;
- replay identity and disabled-field validity;
- controller payload construction and persisted field trace;
- complete pytest suite: 506 passed;
- Ruff and strict mypy for the changed modules: passed.

No developmental state was manually inserted by this implementation. The live
developmental trajectory, frozen C/R/F0 readouts, paired seeds, and blinded
comparison remain pending and must use a separately frozen configuration.
