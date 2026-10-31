# Proposed low-cost experiments

**Status: planned, not run.** None of the measurements below are included in the current result tables. The budgets are proposed pilot settings, not evidence of completed training or validated optimal settings.

## 1. Broaden differential encoding coverage

**Question.** Does the pinned MinBPE wrapper continue to agree with `cl100k_base` beyond the eight curated ordinary-text inputs?

Create a deterministic input set containing 500 short strings across Latin letters, German and Spanish diacritics, Chinese, digits, punctuation, repeated whitespace, newlines, combining characters, and emoji. Include composed and decomposed Unicode forms as separate inputs; do not normalize away differences unless the test explicitly evaluates normalization. Generate all inputs with a recorded random seed and save their hashes.

Initialize each tokenizer once, then compare exact token-ID lists and complete-text round trips. Record the number of cases, number of mismatches, and the smallest failing examples. Keep special-token strings in a separately specified test set with explicit `allowed_special` settings; ordinary-text agreement does not imply complete special-token API equivalence. Any expected failure should be labeled and explained, rather than counted as a successful round trip.

**Cost and output.** CPU only, short strings, no training or paid API. Produce `results/encoding_coverage.json` and a compact coverage table. Treat this as a stronger behavioral check, not a model-quality benchmark or a proof over all Unicode inputs.

## 2. Run a small German/Spanish ratio pilot

**Question.** Under a fixed training budget and tokenizer configuration, how does the language share affect held-out sequence length within each language?

Start with a small, redistributable or locally accessible corpus whose source, license, and document boundaries can be recorded. Normalize consistently to NFC, deduplicate before splitting, and reserve separate validation and test documents for each language. Match domains as closely as practical. Record Unicode code-point counts, including spaces and punctuation, and keep a record of actual ratios after selecting complete text units.

A low-cost first pass can use a **200,000-character total training budget**, a **512-token ordinary vocabulary** including the 256 byte tokens, three ratios (**30:70, 50:50, 70:30**), and sampling seeds **0, 1, 2**. Hold out approximately **20,000 characters per language** for validation and the same amount for a final test, reducing all budgets consistently if unique text is insufficient. These settings deliberately scale down the larger unexecuted design in the technical report. Check the training tool's runtime on one configuration before running the full grid; an efficient byte-level BPE implementation may be preferable to educational MinBPE at larger scales.

Use the same pre-tokenization, special-token policy, training budget, vocabulary size, and held-out text for every candidate. Sample without replacement; if a candidate is infeasible, reduce the common budget or mark it infeasible rather than silently repeating text. Select a ratio on validation data and evaluate it once on the untouched test data.

Measure total ordinary-text tokens divided by total characters **separately for German and Spanish**. Also report the relative change against the 50:50 baseline, the range across seeds, document-length percentiles in tokens, and round-trip integrity. For a three-seed pilot, show the observed range rather than implying a well-estimated confidence interval. Inspect some German compounds and Spanish accented/inflected words as diagnostics.

**Cost and output.** Nine small tokenizer trainings on CPU; no language-model training. Produce a corpus manifest, fixed split/seed configuration, per-language metrics, and a plot of the trade-off. Do not interpret shorter sequences alone as improved language understanding or claim a universal best ratio.

## 3. Isolate the effect of pre-tokenization

**Question.** Which segmentation changes arise from regular-expression boundaries rather than the merge-counting rule itself?

Train `BasicTokenizer` and `RegexTokenizer` on the **same fixed 20,000-character controlled corpus**, with a **512-token vocabulary** and an explicit recorded regex pattern. Include prose, long compounds, accented words, numbers, whitespace, and short mixed-language passages. Use a separate fixed evaluation set. Keep all other choices identical, including normalization, training order, and special-token policy.

Compare token counts within each input category, exact round trips, and examples of merges that cross a boundary in `BasicTokenizer` but are prevented by regex pre-tokenization. Save the learned rules and identify concrete segmentation examples that explain the aggregate differences. If timing is added, record the environment and repeat measurements; a single elapsed time should not be presented as a reliable speed comparison.

**Cost and output.** Two small CPU trainings using existing dependencies. Produce an ablation table and a few source-linked examples. This isolates one implementation choice without claiming that either tokenizer is generally better.
