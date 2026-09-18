# MNEME project documents

The documents are preserved in their supplied form and are intentionally not merged.

* `specifications/MNEME_Model_Instance_Development_Spec.md` is the current normative
  architecture and research definition (revision 2026-09-13).
* `specifications/MNEME_Development_Roadmap.md` is the normative implementation sequence
  (dated 2026-09-14; P0.1 is the current boundary).
* `research/MNEME_Research_Amendment_Individuality_Identity_2026-09-14.md` is later
  research context and supersedes earlier related-work interpretations where they conflict.
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
* [P0.4 FakeHost integrated receipt](receipts/MNEME_P0.4_Fake_Integrated_Receipt.md)
  records the integrated no-learning runner and network-free validation. The bounded
  real Gemma baseline remains an explicit external acceptance gate.

The P0.2 implementation is now present under `src/mneme/state/`; its acceptance
status and receipts are recorded in `.codex/work-queue.json` and `bible.md`.
The P0.3 implementation is present under `src/mneme/experiments/`; its acceptance
status and receipt are recorded in `.codex/work-queue.json` and `bible.md`.

This repository does not contain the older `MNEME_Earned_Association_Field_Spec.md`; the
current specification identifies it as historical context.
