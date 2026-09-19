# MNEME project documents

The documents are preserved in their supplied form and are intentionally not merged.

* `specifications/MNEME_Model_Instance_Development_Spec.md` is the current normative
  architecture and research definition (revision 2026-09-13).
* `specifications/MNEME_Development_Roadmap.md` is the normative implementation sequence
  (dated 2026-09-14; P0.1 is the current boundary).
* `research/MNEME_Research_Amendment_Individuality_Identity_2026-09-14.md` is later
  research context and supersedes earlier related-work interpretations where they conflict.
* `research/MNEME_Developmental_Dynamics_Amendment_2026-09-19.md` is preserved unchanged
  as design context, with its Phase One allocation recorded in the approved graph-wrapper
  preview plan below. Adaptive developmental dynamics remain Phase Two or later;
  plan approval does not authorize implementation.
* `research/MNEME_Related_Work_Research_Dossier.docx` is unchanged historical/reference
  material, not a normative implementation specification.
* `setup/deepinfra.md` is the operational procedure for the selected live P0.1 backend.
* [Approved P0.2 durable lineage, history, and checkpoints plan](<Approved Plans/MNEME_P0.2_Durable_Lineage_History_Checkpoints_Plan.md>)
  records the approved implementation design and its three scope amendments: no
  future-mechanism Python placeholders, storage and export/copy permissions only,
  and an accepted-history digest without behavioral-equivalence claims.
  P0.2 implementation and its acceptance receipts are complete; later phases remain out of scope.
* [Approved P0.3 experiment contracts and experimental isolation plan](<Approved Plans/MNEME_P0.3_Experiment_Contracts_Experimental_Isolation_Plan.md>)
  records the versioned experiment identity, split controls, random streams, capability
  preflight, budgets, frozen evaluation boundary, and four implementation chunks. P0.3
  implementation and its FakeHost acceptance receipt are complete.
* [P0.4 FakeHost integrated receipt](receipts/MNEME_P0.4_Fake_Integrated_Receipt.md) ([JSON](receipts/MNEME_P0.4_Fake_Integrated_Receipt.json)) and [real Gemma baseline receipt](receipts/MNEME_P0.4_Real_Gemma_Baseline_Receipt.md) ([JSON](receipts/MNEME_P0.4_Real_Gemma_Baseline_Receipt.json)) record the completed no-learning laboratory.
* [Approved Phase One graph-wrapper preview plan](<Approved Plans/MNEME_Phase_One_Graph_Wrapper_Preview_Plan.md>)
  preserves the P1.1/P1.2/P1.3 gates and incorporates fixed route ranking without
  confidence/salience bonuses, distinct revision/episode/graph/self-view counters,
  and explicit development-enabled creation with fail-closed legacy reuse.
  P1.1, P1.2, and the credential-free P1.3 preview implementation are present;
  the required bounded live acceptance remains blocked by strict live extraction
  validation, not provider availability ([historical receipt](receipts/MNEME_Phase_One_Live_Acceptance_Blocker.md),
  [fresh failure receipt](receipts/MNEME_Phase_One_Live_Acceptance_Fresh_Failure_Receipt.md)).
  The offline adversarial remediation and machine-readable validation are recorded in
  [the Phase One remediation receipt](receipts/MNEME_Phase_One_Adversarial_Audit_Remediation_Receipt.md).
* [Phase One live remediation receipt](receipts/MNEME_Phase_One_Live_Remediation_Receipt.md)
  records the corrected extraction contract, durable naming accounting, and
  offline validation before the newly authorized bounded live run. DeepInfra
  access is functional; the historical 18-call failure remains preserved.
* [Phase One extractor quotation remediation receipt](receipts/MNEME_Phase_One_Extractor_Quote_Remediation_Receipt.md)
  records the follow-up offline correction that moves Unicode span arithmetic
  into deterministic software while retaining strict source provenance. No new
  live call was made; the remaining live budget is unchanged.
* [Phase One corrected-contract live failure receipt](receipts/MNEME_Phase_One_Live_Acceptance_Quote_Run_Failure_Receipt.md)
  records the first four-call run under the quotation contract: DeepInfra
  returned valid source-backed edges, but no required route, so P1.1 stopped
  and P1.2/P1.3 were not attempted.
* [Phase One corrected-contract human-review evidence bundle](receipts/MNEME_Phase_One_Live_Acceptance_Quote_Run_Review_Evidence.md)
  preserves the sanitized developmental inputs, host responses, extractor
  template and outputs, resolution decisions, graph state, and route decision
  from that run. It is an addendum; the original failure receipt is unchanged.
* [Phase One graph-wrapper preview runbook](PHASE_ONE_PREVIEW_RUNBOOK.md) documents
  the read-only matched no-memory, lexical, and graph comparison path.

The P0.2 implementation is now present under `src/mneme/state/`; its acceptance
status and receipts are recorded in `.codex/work-queue.json` and `bible.md`.
The P0.3 implementation is present under `src/mneme/experiments/`; its acceptance
status and receipt are recorded in `.codex/work-queue.json` and `bible.md`.

This repository does not contain the older `MNEME_Earned_Association_Field_Spec.md`; the
current specification identifies it as historical context.
