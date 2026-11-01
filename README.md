# Byte-Level BPE Analysis and Multilingual Sampling Design

**[Read the full report online (中文)](reports/online.md)** · [View the typeset PDF](https://gofish040821.github.io/byte-bpe-multilingual-sampling/reports/tokenizer_analysis_report.pdf)

This study traces how MinBPE learns and applies merge rules. It compares the wrapper's token IDs with `cl100k_base` on eight selected ordinary-text inputs and calculates character quotas for a proposed German/Spanish tokenizer experiment.

[Report and figure access](reports/README.md) · [Research scope](docs/PROJECT_SCOPE.md) · [Detailed project experience](docs/PROJECT_EXPERIENCE.md) · [Structured record](experience/project.json)

## Research questions

| Question | Operational method | Evidence |
| --- | --- | --- |
| How do adjacent-pair counts, disjoint replacements, and learned ranks determine BPE behavior? | Instrument a fixed implementation and construct a rank-versus-frequency counterexample. | [Merge traces](results/bpe_walkthrough.json) |
| Do the two encoders return the same token IDs on the eight selected inputs? | Compare ID lists and full-text round trips, then inspect regex boundaries and byte-ID remapping. | [Encoding results](results/gpt4_check.json) |
| How can language proportions be selected under explicit tokenizer-training constraints? | Implement smoothed quota allocation and specify normalization, fixed budgets, document splits, and within-language evaluation. | [Quota calculations](results/language_mix.json) and [experimental design](reports/content/multilingual_sampling.json) |

<a name="findings"></a>

## Worked example and verification results

### How MinBPE counts and applies a merge

After the first training round on `abababab`, the sequence contains four copies of the token `ab` (ID 256). Number them 1 through 4. In round two, MinBPE learns **one rule**, `(ab, ab) → abab` (ID 257). The trace records two quantities for this rule.

| Operation | Token positions | Recorded value |
| --- | --- | --- |
| [Count occurrences](vendor/minbpe/base.py#L13-L23) of the adjacent token pair `(ab, ab)` | (1,2), (2,3), (3,4) | **3 matching windows** |
| [Apply the rule](vendor/minbpe/base.py#L25-L41) from left to right | (1,2), (3,4) | **2 replacements**, yielding `[257, 257]` |

The first replacement consumes tokens 1 and 2, so the scan resumes at token 3. This accounts for both numbers. The same trace gives **4 windows and 4 replacements** in round one and **1 of each** in round three. Overlap in the second round explains why its counts differ. [Recorded training steps](results/bpe_walkthrough.json)

![Four copies of token 256, with three matching windows on the left and two disjoint replacements on the right](figures/overlap.png)

### What each check covers

| Check | Input and observed result | Evidence |
| --- | --- | --- |
| Training trace | With a final vocabulary of 259, `BasicTokenizer` reduces `abababab` from 8 tokens to 4, then 2, then 1. The vocabulary grows from 256 to 259 entries. The resulting tokenizer encodes `ababab` as `[257, 256]`. | [Trace figure](figures/bpe_merges.png) |
| Learned merge order | Training on `ab1ab2ab3ab4bcbcbc` gives `ab` priority over `bc`. On the new input `abcbcbcbc`, MinBPE follows that order and returns `[256,99,257,257,257]`. A comparison that selects the most frequent pair in the new input first returns `[97,257,257,257,257]`. | [Counterexample](results/bpe_walkthrough.json) |
| Encoding comparison | On **8 selected ordinary-text inputs**, the MinBPE wrapper and `tiktoken`'s `cl100k_base` return identical IDs and reconstruct each input. The combined suite passes **17 grouped checks** across the BPE trace, wrapper and additional cases. | [Inputs and IDs](results/gpt4_check.json) · [Check list](results/verification.json) |
| Sampling arithmetic | **4 checks** cover integer budget conservation, shares summing to one, the square-root allocation for a 9:1 inventory, and zero quota for an empty source. The German/Spanish inventories are hypothetical. Comparing tokenizer quality on real text is a proposed experiment. | [Quotas and checks](results/language_mix.json) |

## Methods

**Mechanism tracing and source audit.** The analysis calls the pinned upstream `BasicTokenizer`, `get_stats`, and `merge` functions and records intermediate IDs, pair frequencies, chosen rules, and actual replacement counts. Source analysis covers 19 blocks and 184 displayed execution lines, including regex pre-tokenization, merge-rank recovery, byte-ID remapping, and decoding. Detailed foundations and line-by-line annotations are retained as report appendices.

**Differential verification.** The harness initializes MinBPE's `GPT4Tokenizer` wrapper and `tiktoken`'s `cl100k_base`, then compares exact ID lists and complete-text reconstruction for English, German, Spanish, Chinese, digits, newlines, emoji, and empty input. Byte-level inspection preserves token contents that cannot be decoded individually as UTF-8.

**Multilingual design.** Candidate shares use a common character-count unit:

$$q_l=\frac{n_l^\alpha}{\sum_j n_j^\alpha},\qquad 0\leq\alpha\leq1.$$

For an **assumed** German/Spanish inventory of 9 million/1 million Unicode code points and a 1 million-character budget, the executed allocator gives:

| Exponent | German share / quota | Spanish share / quota |
| --- | --- | --- |
| `0` | 50% / 500,000 | 50% / 500,000 |
| `0.5` | 75% / 750,000 | 25% / 250,000 |
| `1` | 90% / 900,000 | 10% / 100,000 |

The proposed corpus study holds normalization, total training budget, vocabulary size, document-level splits, and evaluation text fixed. It compares token counts per character within each language against a 50:50 baseline. [Three follow-up experiments](docs/EXTENSIONS.md) specify broader encoding coverage, a small ratio pilot, and a pre-tokenization ablation.

## Artifacts

| Artifact | PDF access | Data and editable sources |
| --- | --- | --- |
| Full technical report | [View PDF](https://gofish040821.github.io/byte-bpe-multilingual-sampling/reports/tokenizer_analysis_report.pdf) · [Download](https://raw.githubusercontent.com/gofish040821/byte-bpe-multilingual-sampling/main/reports/tokenizer_analysis_report.pdf) | [Report content](reports/content/) · [LaTeX source](reports/latex/main.tex) |
| Merge mechanism | [View PDF](https://gofish040821.github.io/byte-bpe-multilingual-sampling/figures/bpe_merges.pdf) · [Download](https://raw.githubusercontent.com/gofish040821/byte-bpe-multilingual-sampling/main/figures/bpe_merges.pdf) · [PNG](figures/bpe_merges.png) | [CSV](figures/bpe_merges.csv) · [TikZ](reports/latex/figures/bpe_merges.tex) |
| Counting mechanism | [View PDF](https://gofish040821.github.io/byte-bpe-multilingual-sampling/figures/overlap.pdf) · [Download](https://raw.githubusercontent.com/gofish040821/byte-bpe-multilingual-sampling/main/figures/overlap.pdf) · [PNG](figures/overlap.png) | [CSV](figures/overlap.csv) · [TikZ](reports/latex/figures/overlap.tex) |
| Sampling scenario | [View PDF](https://gofish040821.github.io/byte-bpe-multilingual-sampling/figures/language_sampling.pdf) · [Download](https://raw.githubusercontent.com/gofish040821/byte-bpe-multilingual-sampling/main/figures/language_sampling.pdf) · [PNG](figures/language_sampling.png) | [CSV](figures/language_sampling.csv) · [PGFPlots](reports/latex/figures/language_sampling.tex) |

The [web edition](reports/online.md) includes the full report and source annotations. The PDF links open the original typeset files on GitHub Pages.

All four PDFs are accompanied by the code and sources required to inspect the analysis. Three PNG previews, seven CSV/JSON figure tables, and a [figure provenance manifest](figures/manifest.json) are also included. The report leads with the research framework, observed results, and multilingual design; explanatory derivations and source annotations follow in appendices. Edited AI-interaction records are retained with the report sources as supplementary provenance.

## Reproduce

Recorded environment: **Python 3.12.14 on Windows**, `regex==2026.9.29`, and `tiktoken==0.14.0`. The analysis runs on CPU without model API credentials. Other Python versions and operating systems have not been validated here.

From the repository root in an activated Python environment:

```sh
python -m pip install -r requirements.txt
python code/verify.py
python code/language_mix.py
python code/export_figure_data.py --verify-existing
```

`verify.py` regenerates BPE traces, encoding comparisons, and their JSON/TXT summaries. `language_mix.py` calculates the quota scenario. The final command verifies the seven figure tables before rewriting them. To inspect a different inventory:

```sh
python code/language_mix.py --de-chars 9000000 --es-chars 1000000 --total-chars 1000000
```

`tiktoken` may download its public encoding data on the first run. The ignored `.cache/tiktoken` directory stores that data; `TIKTOKEN_CACHE_DIR` can select another cache.

For local link, provenance, artifact-hash, and publication checks:

```sh
python -m pip install -r requirements-dev.txt
python code/validate_repository.py
```

Recorded local validation is in [repository_validation.json](results/repository_validation.json).

### Rebuild the technical report

The build tools use Python's standard library and an external **Tectonic** executable. Uncached TeX packages require network access. **Poppler** is optional for PNG/SVG exports; see [report dependencies](reports/requirements-report.txt).

```sh
python code/build_online_report.py
python code/build_latex_report.py --check-only
python code/compile_report.py --png
```

Pass `--tectonic` if the executable is not on `PATH`. PNG export requires `pdftoppm`; `--svg` requires `pdftocairo`. Edit `reports/content/` for prose and `reports/latex/figures/` for diagrams. The builder regenerates `main.tex`; compiled pages require visual inspection after changes.

## Scope and limitations

The eight curated cases provide bounded differential evidence, rather than comprehensive input coverage or complete special-token compatibility. Sampling results are arithmetic on assumed inventories: no real German/Spanish ratio sweep or downstream language-model evaluation has been run, and no universal optimal ratio, accuracy gain, perplexity reduction, or speedup is claimed. Proposed experiments are kept separate from recorded results in [EXTENSIONS](docs/EXTENSIONS.md).

## Attribution and references

The mechanism implementation is unchanged [MinBPE](https://github.com/karpathy/minbpe/tree/1acefe89412b20245db5a22d2a02001e547dc602), pinned at `1acefe89412b20245db5a22d2a02001e547dc602`, with its original [MIT license](vendor/LICENSE) and [source hashes](vendor/provenance.json). Project-specific analysis, wrappers, verification, figures, and report were developed with Codex assistance. [CONTRIBUTIONS](docs/CONTRIBUTIONS.md) records that provenance.

- OpenAI, [tiktoken](https://github.com/openai/tiktoken): reference implementation for the `cl100k_base` comparison.
- Zhang et al. (2022), [How Robust is Neural Machine Translation to Language Imbalance in Multilingual Tokenizer Training?](https://arxiv.org/abs/2204.14268): tokenizer-training imbalance in the authors' evaluated setting.
- Rust et al. (2021), [How Good is Your Tokenizer? On the Monolingual Performance of Multilingual Language Models](https://aclanthology.org/2021.acl-long.243/): language-specific segmentation diagnostics.
- Chung et al. (2023), [UniMax: Fairer and more Effective Language Sampling for Large-Scale Multilingual Pretraining](https://arxiv.org/abs/2304.09151): sampling balance, counting units, and repetition controls.

[REFERENCES](docs/REFERENCES.md) details the use and scope of these sources. [NOTICE](NOTICE.md) records licensing. The [experience narrative](docs/PROJECT_EXPERIENCE.md) and [structured project record](experience/project.json) connect the artifacts to project-review and CV use.
