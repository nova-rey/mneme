# SAA ten-thread invalid attempt: local host UTF-8 transport

- Run: `p23-saa-ten-thread-20260927-r3`
- Root: `/tmp/mneme-p23-saa-ten-thread-20260927-r3`
- Terminal coordinate: `dev-C-T01-6`
- Disposition: `INVALID_INSTRUMENTATION`
- Provider/local role: local Gemma development response
- Failure: the SSH subprocess used strict UTF-8 text decoding and raised `UnicodeDecodeError` while reading the llama.cpp stream.
- Downstream work: no extraction, assessment, learner update, or later coordinate was accepted for this failed call.
- Historical evidence: unchanged; this is a new prospective invalid attempt.

Correction: the shared local-host transport now decodes the captured UTF-8 stream with replacement handling at the process boundary, preserving the model call path while preventing a transport-only decode exception from invalidating a valid participant response. The uncertain coordinate is not retried in place; the prospective schedule restarts with a new run ID after validation.
