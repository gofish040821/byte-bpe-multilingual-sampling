# Project experience: Byte-Level BPE Analysis and Multilingual Sampling Design

**Research area:** Tokenizer analysis, behavioral verification, and multilingual experiment design.

**Project evidence updated:** 2026-11-01.
**Ownership:** The project owner confirms that this is a project they handled. The work was developed with AI assistance; the upstream MinBPE implementation retains its original attribution.

This record describes the experience represented by this repository. It gives future agents enough context to assess the work and draft evidence-based CV descriptions. It covers this research project, rather than the owner's entire academic or employment history.

## Read this project in order

1. Read the [README](../README.md) for the executable entry points and environment.
2. Read this experience record and the [machine-readable project card](../experience/project.json).
3. Read the [full Chinese technical report](../reports/tokenizer_analysis_report.pdf), beginning with the research framework, measured results, and multilingual sampling design; explanatory foundations and source annotations are retained in appendices.
4. Inspect the [behavior checks](../results/verification.json), [encoding cases](../results/gpt4_check.json), [quota calculations](../results/language_mix.json), [multilingual pilot](../results/quota_pilot.json), and [repository validation](../results/repository_validation.json).
5. Consult [contribution provenance](CONTRIBUTIONS.md), [research references](REFERENCES.md), and the [retained AI-interaction record](../reports/content/ai_interaction_full.json) when determining the wording of a personal contribution.

## Research questions and goals

The project investigates how byte-level Byte Pair Encoding (BPE) learns and applies merge rules, how those rules map to a concrete implementation, and how language proportions could be selected for a German/Spanish BPE tokenizer. It develops an inspectable technical record: executable traces of algorithm behavior, fixed-version source analysis, structured results, scientific figures, and a reproducible report build.

The main goals were to connect BPE training and inference to the source code, verify a GPT-style tokenizer wrapper on concrete inputs and measure how a change in tokenizer-training mix affects a small bilingual language model.

## Methods and work carried out

### 1. Instrumented byte-level BPE and source analysis

The walkthrough calls the pinned upstream `BasicTokenizer`, `get_stats`, and `merge` functions while recording each intermediate sequence, all adjacent-pair frequencies, the chosen pair, the new token ID, and the number of actual replacements. This makes the algorithm trace independently inspectable instead of relying only on a prose explanation.

For `abababab`, sequence lengths are **8 → 4 → 2 → 1** as vocabulary sizes grow **256 → 257 → 258 → 259**. In round two the four tokens each represent `ab` (ID 256). The pair `(256, 256)` matches at positions 1–2, 2–3 and 3–4. A left-to-right merge consumes positions 1–2 together, then 3–4 together, yielding two `abab` tokens (ID 257). The trace verifies how `get_stats` counts matching windows and how `merge` consumes two input tokens per replacement. [Recorded trace](../results/bpe_walkthrough.json) · [Source functions](../vendor/minbpe/base.py)

A separate, executed counterexample trains on `ab1ab2ab3ab4bcbcbc`, learning `ab → 256` before `bc → 257`. On new input `abcbcbcbc`, `bc` is initially more frequent, but the earlier learned `ab` rule still takes priority. Correct encoding produces `[256,99,257,257,257]`; an intentionally wrong frequency-first rule produces `[97,257,257,257,257]`. This connects a concrete failure mode to the source-level distinction between training and inference.

The report annotates **19 source blocks and 184 displayed execution lines** across `base.py`, `basic.py`, `regex.py`, and `gpt4.py`. Its line numbers refer to one fixed MinBPE commit. The analysis covers regular-expression pre-tokenization, special-token dispatch, merge-rank recovery, byte-ID remapping, and the wrapper's decoding and training limitations.

### 2. Differential encoding and Unicode checks

The comparison harness runs the MinBPE `GPT4Tokenizer` wrapper and `tiktoken`'s `cl100k_base` on eight individual inputs covering English, German, Spanish, Chinese, digits, newlines, emoji and empty input. On each of these eight inputs the token IDs match exactly and decoding recovers the original text. The **17 grouped behavioral checks** cover the wider harness, including the BPE trace, those input comparisons and additional encoding checks.

The recorded examples include `Hello, world! → [9906,11,1917,0]` and the three-digit regex chunks for `1234567890`. They also expose how individual tokens can contain incomplete UTF-8 byte sequences and therefore require concatenation before decoding. The byte-remapping examples distinguish raw byte values from `cl100k_base` single-byte token IDs: space byte 32 maps to ID 220, and byte 97 (`a`) maps to ID 64.

This work loads an existing encoding. It does not train GPT-4 or run a model API. The cases support agreement for the supplied ordinary inputs; they do not establish correctness for every Unicode string or complete compatibility for special-token behavior.

### 3. Literature synthesis and multilingual sampling design

The project reviews three sources: Zhang et al. on language imbalance in multilingual tokenizer training, Rust et al. on tokenizer quality and language-specific segmentation, and Chung et al.'s UniMax language sampling. The report records each paper's scope so that a machine-translation result or a model-pretraining result is not silently treated as direct proof of an optimal tokenizer ratio.

The quota calculator implements exponent-smoothed shares:

$$q_l=\frac{n_l^\alpha}{\sum_j n_j^\alpha},\qquad 0\leq\alpha\leq1.$$

For the explicitly assumed inventory of **9 million German / 1 million Spanish characters** and a **1 million-character budget**, the executed settings yield:

| Exponent | German quota | Spanish quota |
| --- | ---: | ---: |
| 0 | 500,000 | 500,000 |
| 0.5 | 750,000 | 250,000 |
| 1 | 900,000 | 100,000 |

**Four arithmetic and boundary checks pass**, including integer quotas summing to the budget and zero-inventory language handling. These are mathematical calculations with hypothetical inventories.

The larger design in the report proposes a five-million-character budget, an 8,192-entry vocabulary and a validation stage to select a ratio. A smaller controlled experiment tested the three quota settings on public German and Spanish text.

### 4. German/Spanish corpus experiment

The tokenizer-training mix varied across 50:50, 75:25 and 90:10 German:Spanish. Each mix used the same three sampling seeds and 512-entry vocabulary. This tests how the 9:1 inventory scenario would allocate a 50,000-character tokenizer budget on actual text. The 9:1 ratio is a scenario assumption. The observed corpus sizes are recorded separately.

The language model for each tokenizer was a smoothed bilingual bigram trained on the same German and Spanish GSD sentences. The independent PUD test collection contains aligned texts in both languages. The score sums the probabilities of all ways the model could generate each test sentence and expresses the cost per byte. German and Spanish carry equal weight in the aggregate. See the [source and license record](REFERENCES.md#pilot-corpora) and [per-run results](../results/quota_pilot.json).

All nine models used the same 1,500 training sentences per language and the same 1,000 PUD test sentence pairs from 397 documents. The table gives byte perplexity. Each entry exponentiates the mean bits per byte across the three seeds. The final column gives each language equal weight in log space. Lower is better.

| German:Spanish tokenizer quota | German | Spanish | Equal-language score |
| --- | ---: | ---: | ---: |
| 50:50, equal-share reference | 8.8404 | 7.7380 | 8.2709 |
| 75:25, square-root smoothing | 8.6282 | 7.9340 | 8.2738 |
| 90:10, proportional baseline | 8.5383 | 8.2858 | 8.4111 |

In the planned comparison with proportional sampling, smoothing from 90:10 to 75:25 reduced aggregate byte perplexity by 1.63%. Spanish improved by 4.25% while German worsened by 1.05%. All three paired seeds had a lower aggregate score with smoothing. Across 4,000 paired resamples of the test documents, the middle 95% of aggregate changes ranged from −1.77% to −1.49%, conditional on the fitted models. The 50:50 reference scored slightly better than 75:25 on the aggregate, by about 0.04%. [Document scores](../results/quota_pilot_documents.csv) · [Paired bootstrap](../results/quota_uncertainty.json)

### 5. Reproducible reporting and public project engineering

The project includes a **full LaTeX technical report** organized around research questions, methods, results, and experimental design, followed by appendices for explanatory foundations and source annotations. Standard mathematical notation and **three native TikZ/PGFPlots vector figures** support the analysis. Two figures illustrate executed BPE behavior; one depicts the explicitly assumed sampling scenario. Seven CSV/JSON tables preserve the figure data and provenance. The exporter uses fixed LF line endings for stable data output.

The local project was reorganized into code, documentation, report content, TeX sources, results, figures, and pinned upstream software. Scripts locate the project relative to their own files; the PowerShell launcher accepts the active Python interpreter. Optional Tectonic and Poppler tools rebuild the report and image exports. The retained algorithm runs use **Python 3.12.14 on Windows, regex 2026.9.29, and tiktoken 0.14.0**.

The publication preparation removes personal machine paths from public results and interaction records, omits identity fields and PDF author values, excludes downloaded vocabularies and build caches from Git, and preserves upstream licensing and source hashes. The repository checker validates local Markdown links, source/artifact hashes, explicit identity fields, selected machine-path patterns, and PDF author metadata. It cannot infer unknown personal information.

## Contribution and tool-use provenance

The owner handled the project and directed the analysis scope, report organization, presentation revisions, and reproducible publication of its artifacts. Repository-specific walkthroughs, checks, analysis, documentation, figures, and report tooling were generated and revised with Codex assistance. Retained interactions document that workflow, including literature checks and review prompts; machine paths in the public record were redacted.

The BPE implementation in `vendor/minbpe/` is unchanged upstream software, not a new algorithm or a project-authored reimplementation. Fixed commit `1acefe89412b20245db5a22d2a02001e547dc602`, the original MIT notice, and file hashes preserve this distinction. Project-specific work and upstream implementation remain separately attributed in the retained provenance record.

## Evidence map for future CV agents

| Potential experience theme | Concrete evidence | Appropriate interpretation |
| --- | --- | --- |
| Algorithm analysis | [Walkthrough](../code/bpe_walkthrough.py), [trace](../results/bpe_walkthrough.json) | Analyzed and instrumented byte-level BPE behavior, including an inference counterexample. |
| Source reading | [Report](../reports/tokenizer_analysis_report.pdf), [content](../reports/content/bpe_analysis.json) | Connected algorithm steps to a pinned source implementation and documented encoding mechanisms. |
| Behavioral verification | [Harness](../code/gpt4_check.py), [17 checks](../results/verification.json) | Compared exact token IDs and round trips on eight curated ordinary-text cases. |
| Research design | [Proposal](../reports/content/multilingual_sampling.json), [references](REFERENCES.md) | Synthesized literature into a controlled, unexecuted multilingual-tokenizer evaluation plan. |
| Numerical implementation | [Quota allocator](../code/language_mix.py), [results](../results/language_mix.json) | Implemented and checked hypothetical sampling-budget arithmetic. |
| Controlled language-model evaluation | [Pilot code](../code/quota_pilot.py), [nine runs](../results/quota_pilot.json) | Varied tokenizer-training shares, held language-model training text fixed and compared held-out code lengths per byte. |
| Reproducibility | [Build script](../code/compile_report.py), [validation](../results/repository_validation.json) | Packaged code, evidence, pinned dependencies, data exports, report sources, and portable entry points. |
| Technical communication | [Three figures](../figures/manifest.json), [report](../reports/tokenizer_analysis_report.pdf) | Produced a detailed explanation and native vector visualizations with AI assistance. |

When describing the multilingual experiment, name the training and test corpora, model type, baseline and unit of evaluation. The seed repeats vary the tokenizer-training sample on a common test collection. A claim about downstream accuracy would require a separate labeled task.

The [machine-readable project card](../experience/project.json) provides the same factual anchors for automated CV aggregation. The [CV descriptions](CV_DESCRIPTIONS.md) are a starting point; future agents should adapt emphasis to a target role while retaining evidence and attribution.
