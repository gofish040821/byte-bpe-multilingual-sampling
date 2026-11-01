# Technical report and figure access

The report presents the research framework, observed encoding results, multilingual sampling design, and source-audit appendix. The three standalone vector figures are supplied with PNG previews, data, and editable LaTeX sources.

| Document | Direct PDF download | Repository preview | Image preview |
| --- | --- | --- | --- |
| Full technical report | [Download](https://raw.githubusercontent.com/gofish040821/byte-bpe-multilingual-sampling/main/reports/tokenizer_analysis_report.pdf) | [PDF](tokenizer_analysis_report.pdf) | — |
| BPE merge trace | [Download](https://raw.githubusercontent.com/gofish040821/byte-bpe-multilingual-sampling/main/figures/bpe_merges.pdf) | [PDF](../figures/bpe_merges.pdf) | [PNG](../figures/bpe_merges.png) |
| Overlapping windows and replacement | [Download](https://raw.githubusercontent.com/gofish040821/byte-bpe-multilingual-sampling/main/figures/overlap.pdf) | [PDF](../figures/overlap.pdf) | [PNG](../figures/overlap.png) |
| Multilingual sampling scenario | [Download](https://raw.githubusercontent.com/gofish040821/byte-bpe-multilingual-sampling/main/figures/language_sampling.pdf) | [PDF](../figures/language_sampling.pdf) | [PNG](../figures/language_sampling.png) |

## If the embedded PDF preview fails

GitHub's file page may display **Unable to render code block** instead of its PDF preview. Click **Download** above, or use the download-arrow button on the file page, then open the saved PDF in a browser or PDF reader. Direct downloads bypass the embedded preview; access to `raw.githubusercontent.com` is required.

The public downloads were checked on **2026-11-01**: all four returned HTTP 200, matched the local files byte for byte, and parsed successfully. The full report contains 25 pages; its downloaded first page was also rendered and visually checked. These checks establish file integrity; they do not diagnose a visitor's browser or network. See the [access check record](../results/repository_validation.json).

For editable material, see [report content](content/), [LaTeX source](latex/main.tex), and the [artifact catalog](../README.md#artifacts).
