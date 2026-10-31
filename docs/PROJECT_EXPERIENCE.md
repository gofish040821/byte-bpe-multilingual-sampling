# Project experience: Byte-Level BPE Analysis and Multilingual Sampling Design

**Research area:** Tokenizer analysis, behavioral verification, and multilingual experiment design.

**Documented artifact and validation date:** 2026-10-31.
**Ownership:** The project owner confirms that this is a project they handled. The work was developed with AI assistance; the upstream MinBPE implementation retains its original attribution.

This record describes the experience represented by this repository. It gives future agents enough context to assess the work and draft evidence-based CV descriptions. It covers this research project, rather than the owner's entire academic or employment history.

## Read this project in order

1. Read the [README](../README.md) for the executable entry points and environment.
2. Read this experience record and the [machine-readable project card](../experience/project.json).
3. Read the [full Chinese technical report](../reports/tokenizer_analysis_report.pdf), beginning with the research framework, measured results, and multilingual sampling design; explanatory foundations and source annotations are retained in appendices.
4. Inspect the [behavior checks](../results/verification.json), [encoding cases](../results/gpt4_check.json), [quota calculations](../results/language_mix.json), and [repository validation](../results/repository_validation.json).
5. Consult [contribution provenance](CONTRIBUTIONS.md), [research references](REFERENCES.md), and the [retained AI-interaction record](../reports/content/ai_interaction_full.json) when determining the wording of a personal contribution.

## Research questions and goals

The project investigates how byte-level Byte Pair Encoding (BPE) learns and applies merge rules, how those rules map to a concrete implementation, and how language proportions could be selected for a German/Spanish BPE tokenizer. It develops an inspectable technical record: executable traces of algorithm behavior, fixed-version source analysis, structured results, scientific figures, and a reproducible report build.

The main technical goals were to explain the difference between learning merge rules and applying them, understand UTF-8 and token-ID details, verify a GPT-style tokenizer wrapper on concrete inputs, and design a controlled multilingual-tokenizer experiment. The language-ratio part remains an experimental design supported by papers and executable arithmetic; it is not presented as a completed corpus benchmark.

## Methods and work carried out

### 1. Instrumented byte-level BPE and source analysis

The walkthrough calls the pinned upstream `BasicTokenizer`, `get_stats`, and `merge` functions while recording each intermediate sequence, all adjacent-pair frequencies, the chosen pair, the new token ID, and the number of actual replacements. This makes the algorithm trace independently inspectable instead of relying only on a prose explanation.

For `abababab` with a vocabulary of 259 entries, the executed sequence lengths are **8 → 4 → 2 → 1**, while vocabulary sizes grow **256 → 257 → 258 → 259**. The three rounds have pair-frequency/replacement-count pairs **(4,4), (3,2), (1,1)**. The second round explains a subtle distinction: `[256,256,256,256]` has three overlapping adjacent windows, but left-to-right replacement can use only two disjoint pairs.

A separate, executed counterexample trains on `ab1ab2ab3ab4bcbcbc`, learning `ab → 256` before `bc → 257`. On new input `abcbcbcbc`, `bc` is initially more frequent, but the earlier learned `ab` rule still takes priority. Correct encoding produces `[256,99,257,257,257]`; an intentionally wrong frequency-first rule produces `[97,257,257,257,257]`. This connects a concrete failure mode to the source-level distinction between training and inference.

The report annotates **19 source blocks and 184 displayed execution lines** across `base.py`, `basic.py`, `regex.py`, and `gpt4.py`. Its line numbers refer to one fixed MinBPE commit. The analysis covers regular-expression pre-tokenization, special-token dispatch, merge-rank recovery, byte-ID remapping, and the wrapper's decoding and training limitations.

### 2. Differential encoding and Unicode checks

The comparison harness initializes the MinBPE `GPT4Tokenizer` wrapper and `tiktoken`'s `cl100k_base`, then checks exact token-ID equality and full-text round trips on eight ordinary-text categories: English, German, Spanish, Chinese, digits, newlines, emoji, and empty input. **All eight recorded cases agree and round-trip successfully.** The combined verification script reports **17 successful behavioral checks**; some are grouped checks rather than independent datasets.

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

The report's larger proposed experiment fixes NFC normalization, Unicode code-point counting, total training budget, vocabulary size, document-level splits, ordinary-text encoding policy, and random seeds. It proposes evaluating tokens per character separately within each language, using a 50:50 baseline and validation data to select a candidate before final testing. The proposed budgets and comparison thresholds are design choices, not measured improvements. A smaller pilot and two other inexpensive next experiments are described in [EXTENSIONS](EXTENSIONS.md).

### 4. Reproducible reporting and public project engineering

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
| Reproducibility | [Build script](../code/compile_report.py), [validation](../results/repository_validation.json) | Packaged code, evidence, pinned dependencies, data exports, report sources, and portable entry points. |
| Technical communication | [Three figures](../figures/manifest.json), [report](../reports/tokenizer_analysis_report.pdf) | Produced a detailed explanation and native vector visualizations with AI assistance. |

Prefer an **AI-assisted research project in tokenizer analysis, verification, and experiment design** as the overall framing. Numerical claims should identify their measurement unit and scope: 17 behavioral checks, eight text cases, four quota checks, three vector figures. Avoid converting these counts into accuracy gains, model-performance improvements, corpus-scale results, or proof of mastery. No real-corpus language-ratio experiment, language-model training, or universal optimal ratio is recorded here.

The [machine-readable project card](../experience/project.json) provides the same factual anchors for automated CV aggregation. The [CV descriptions](CV_DESCRIPTIONS.md) are a starting point; future agents should adapt emphasis to a target role while retaining evidence and attribution.
