# SAA ten-thread invalid attempt: MSI disconnect during local assessment

- Run: `p23-saa-ten-thread-20260927-r4`
- Root: `/tmp/mneme-p23-saa-ten-thread-20260927-r4`
- Terminal coordinate: `assess-T06-6`
- Disposition: `INVALID_INSTRUMENTATION`
- Completed evidence before stop: 46 developmental transcript coordinates.
- Failure: the SSH connection to `brokeass-msi` (`100.115.208.48`) closed while the pinned local DeBERTa helper was assessing the coordinate. PilotRuntime marked the call `UNCERTAIN`.
- Downstream work: no learner/readout coordinate after this call was accepted.
- Immediate host check: Tailscale reported the MSI offline and a direct SSH health probe timed out; no claim is made about the host's internal cause without access.
- Historical evidence: unchanged; this is a new prospective invalid attempt.

The run is not a behavioral result. The uncertain coordinate will not be retried in place. A fresh prospective run is permitted only after the MSI is reachable and its identity/resources are reverified. The local specialist and frozen schedule remain unchanged.
