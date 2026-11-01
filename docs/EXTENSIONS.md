# Proposed low-cost experiments

These are follow-up experiments. For completed measurements on German and Spanish, see the [quota pilot results](../results/quota_pilot.json).

## 1. Broaden differential encoding coverage

**Question.** Does the pinned MinBPE wrapper continue to agree with `cl100k_base` beyond the eight curated ordinary-text inputs?

Create a deterministic input set containing 500 short strings across Latin letters, German and Spanish diacritics, Chinese, digits, punctuation, repeated whitespace, newlines, combining characters, and emoji. Include composed and decomposed Unicode forms as separate inputs; do not normalize away differences unless the test explicitly evaluates normalization. Generate all inputs with a recorded random seed and save their hashes.

Initialize each tokenizer once, then compare exact token-ID lists and complete-text round trips. Record the number of cases, number of mismatches, and the smallest failing examples. Keep special-token strings in a separately specified test set with explicit `allowed_special` settings; ordinary-text agreement does not imply complete special-token API equivalence. Any expected failure should be labeled and explained, rather than counted as a successful round trip.

**Cost and output.** CPU only, short strings, no training or paid API. Produce `results/encoding_coverage.json` and a compact coverage table. Treat this as a stronger behavioral check, not a model-quality benchmark or a proof over all Unicode inputs.

## 2. Replicate the language-ratio comparison on a second corpus

Repeat the three quota settings and paired sampling seeds on an independently sourced German/Spanish corpus in a different domain. Freeze the splits, ratios, model settings and equal-language scoring rule before training. Fit each language model on the same texts within that corpus. For each language, report test bits per UTF-8 byte and the paired difference from 50:50 for each seed. Check whether the ordering of the settings survives the domain change.

This replication needs nine small CPU runs and a second licensed corpus. It would test whether the result generalizes beyond the [first pilot](../results/quota_pilot.json).

## 3. Isolate the effect of pre-tokenization

**Question.** Which segmentation changes arise from regular-expression boundaries rather than the merge-counting rule itself?

Train `BasicTokenizer` and `RegexTokenizer` on the **same fixed 20,000-character controlled corpus**, with a **512-token vocabulary** and an explicit recorded regex pattern. Include prose, long compounds, accented words, numbers, whitespace, and short mixed-language passages. Use a separate fixed evaluation set. Keep all other choices identical, including normalization, training order, and special-token policy.

Compare token counts within each input category, exact round trips, and examples of merges that cross a boundary in `BasicTokenizer` but are prevented by regex pre-tokenization. Save the learned rules and identify concrete segmentation examples that explain the aggregate differences. If timing is added, record the environment and repeat measurements; a single elapsed time should not be presented as a reliable speed comparison.

**Cost and output.** Two small CPU trainings using existing dependencies. Produce an ablation table and a few source-linked examples. This isolates one implementation choice without claiming that either tokenizer is generally better.
