# MNEME Phase 3.9 Relational Readout — Current Disposition

**Could our small reader recognize relationships in Gemma on new subjects and new wording, rather than just spotting familiar words?** No result yet: Phase 3.9 is **APPARATUS FAILURE / INCOMPLETE**. Neither attempt produced a locally verified feature dataset, reader metrics, or held-out predictions.

## Attempt r1

The original smoke compared representations captured in two-item padded batches with a singleton. Its maximum absolute float16 difference was 1.0, above the corrected 0.5 limit. That comparison did not reproduce the fixed microbatch layout planned for full capture, so it was insufficient to identify a general capture instability. The r1 result remains preserved as an invalid/incomplete apparatus attempt.

## Attempt r2

I preserved r1 and corrected only the repeat check: r2 replayed the same sorted microbatches, saved selected smoke arrays before the assertion, and retained batch-versus-singleton comparison as a diagnostic. The frozen synthetic corpus semantics were reused; no MNEME state, SAA, model treatment, labels, split, domain, or feature layer changed.

The r2 remote process returned exit code 0. An SSH inspection then observed `smoke.json` and `smoke-features.npz` on the RTX 3090 Ti instance. Before these files were copied and hash-verified on the controller, the instance was stopped and SSH became unavailable. They could not be recovered through the authorized transfer path. Therefore I cannot verify their metrics or claim that the r2 smoke passed. No full-corpus capture, reader fit, baseline comparison, or semantic conclusion exists.

## Rental cleanup and charges

All three r2 instances were destroyed, and a fresh Vast account listing showed none of their IDs present. Their IDs were `54230143`, `54230791`, and `54231336`. The r1 instance was `54227145`. The provider invoice attributes $0.067 to r1 and **$5.896** to r2, for **$5.963** total against the authorized $2 cap. That is an overrun of **$3.963**. Instance `54231336` accounts for $4.627 of GPU charges over 18.759 billed hours, $1.225 of storage over 88.199 hours, $0.037 download, and $0.001 upload. The controller watchdog did not destroy the instance at its recorded deadline; after the experiment process ended, the resource remained billable until cleanup was performed on discovery. All three r2 IDs are now destroyed and absent from the account listing.

No new rental should be launched under the existing cap. Continuing the scientific readout requires an owner decision on a new spend limit and a stronger independently supervised rental lifecycle.

## Evidence

- r1 partial artifact root: `/home/nyx/mneme_artifacts/phase39-relational-readout-20261004-r1`
- r2 artifact root: `/home/nyx/mneme_artifacts/phase39-relational-readout-20261005-r2`
- r2 incident receipt: [MNEME_Phase_3_9_Relational_Readout_Vast_R2_Incident_20261008.json](MNEME_Phase_3_9_Relational_Readout_Vast_R2_Incident_20261008.json)
- frozen corpus remains directly available in the committed r1 package; r2 corpus/source hashes, filtered invoices, and locally retained operational receipts are in the incident manifest.
