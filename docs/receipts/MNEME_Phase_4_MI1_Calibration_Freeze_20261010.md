# MI1 calibration freeze

This is the pre-generation freeze for the local MI1 calibration. No calibration generation beyond the previously preserved eight visible-text comprehension calls has run as of this receipt. No scored Test A, B, or C call has run.

The complete 44-coordinate request manifest, source-bank text, run conditions, code hashes, actual site-selection scores, and calibration decision rule are in [the machine-readable freeze](MNEME_Phase_4_MI1_Calibration_Freeze_20261010.json). The prefill-only selector chose KV groups `[(8,0),(2,1),(6,1),(28,1)]`, expanded to 16 query heads; the sparse selector and prefill capture hashes are embedded in that JSON. The source fixture suite remains frozen at SHA-256 `f1a432eda5d18824b286760f6dc3b376d0efe0c59917748372d91ed56aaf8350`.

The calibration uses three fictional directed-reachability tasks, each at seeds 34111 and 34133. It compares no bank, visible-text bank, relevant latent banks at sparse low/moderate/strong exposure, a broad moderate exposure, and a sparse irrelevant bank. It adds one exact repeated MI1 no-bank request and one exact replay through a clean base server built from the same llama.cpp commit and CUDA/CMake settings. All generated requests use the same pinned Gemma Q2 model, reasoning ON, the frozen sampler, streaming evidence capture, and `cache_prompt=false`.

Before any calibration generation, three separate prefill-only captures provide query-site scores. Calibration target banks are compared against one fixed irrelevant reference bank using the frozen Eq. 3 margin and Appendix-C selection rule: one KV group per layer, then the top four layers, expanded to their query heads. Broad exposure is fixed to all 42 query layers and both KV groups. The captured attention tensor reserves 256 prompt-cache positions and appends bank slots after that capacity; unused capacity positions are checked to have zero probability, while prompt mass is summed only over actual prompt tokens. These captures and forward-only bank encodings do not sample tokens and are accounted separately from the generation ceiling.

The output rubric, control gates, duplicate replay checks, and deterministic choice among passing configurations are frozen in the JSON. If visible comprehension, negative controls, deterministic replays, or all candidate configurations fail their thresholds, scored Test A/B/C will not begin. No prompt, source bank, seed, gain level, selector method, parser, or threshold may be changed after observing calibration outputs; a genuine implementation defect must be preserved as a separate revision and the affected evidence remains exploratory.

The new calibration budget is 44 calls; together with the earlier eight, it uses 52 of the 120-call calibration ceiling. The 268 scored calls and 48 untouched confirmation coordinates remain unchanged. The exact planned envelope including confirmation is 368 generations, below the authorized 800-call hard ceiling. No retry is hidden or replaced.

## Native-path pre-generation evidence

The isolated server path is built from llama.cpp commit `4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0`. The exact Q2 Gemma file hash is `79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03`. A disposable attached-bank prefill captured all 42 query layers, eight query heads, finite normalized attention rows, and nonzero final-query attention mass on appended bank slots; it sampled zero tokens. A separate server-lifecycle smoke verified content-different bank replacement, disable, and clear, and rejected missing or enabled prompt caching on all exposed generation routes before decode.

The native validation receipt is held outside Git at `local-canonical:phase4-mi1/native/mi1-native-server-lifecycle/final-content-replacement/validation-receipt.json`, SHA-256 `fceceb7d3d45c0ffc45d7ae4dc98abf05e93d97de11f2d28b51274bd8e037544`. The complete raw receipts, query capture, bank, binaries, build logs, and patch bundle are under `/home/nyx/mneme-artifacts/phase4-mi1/native/`; they are not MNEME state and are not committed as large artifacts.

No semantic or behavioral result is claimed by this pre-generation receipt.
