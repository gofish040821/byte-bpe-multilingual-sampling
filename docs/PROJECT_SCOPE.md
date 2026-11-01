# Research scope and evidence boundaries

This project studies byte-level BPE through source-level analysis, controlled algorithm traces, differential encoding checks and a German/Spanish sampling pilot. The deliverables combine executable analysis, structured results, vector figures, and a reproducible technical report.

## Research questions

| Question | Method | Observable evidence |
| --- | --- | --- |
| How do BPE training and inference choose merge rules? | Trace a controlled byte-level tokenizer, inspect fixed-version source functions, and construct a merge-priority counterexample. | Intermediate sequences, adjacent-pair counts, learned ranks, replacement counts, and source annotations. |
| Does the MinBPE wrapper match `cl100k_base` on the selected ordinary-text inputs? | Compare exact token IDs and round trips. Inspect regex boundaries, UTF-8 bytes and byte-ID remapping. | Eight individual test inputs and the recorded comparison for each. |
| How does the German/Spanish mix used to train the tokenizer affect held-out language-model perplexity? | Keep the language-model text, test text, vocabulary size and scoring rule fixed while varying tokenizer-training quotas. | [Paired pilot results](../results/quota_pilot.json) for three mixtures and three sampling seeds. |

## Project artifacts

- Executable traces for training, encoding, UTF-8 handling, overlapping pair counts, and learned merge priority.
- A fixed-version copy of upstream MinBPE with its original license and provenance hashes.
- Structured JSON/TXT outputs, three native LaTeX vector figures, and their source data.
- A LaTeX technical report builder and independent figure exports.
- Detailed experience documentation, source references, and reproducibility checks.

The upstream algorithm retains its attribution. Project-specific analysis and engineering were developed with AI assistance; see [CONTRIBUTIONS](CONTRIBUTIONS.md).

## Findings supported by the recorded evidence

| Evidence | Confirmed scope | Interpretation boundary |
| --- | --- | --- |
| `results/verification.json` | 17 successful checks covering the supplied BPE and encoding examples. | Does not establish reliability over arbitrary inputs. |
| `results/gpt4_check.json` | Eight ordinary-text inputs match `cl100k_base` token IDs and round-trip successfully. | Coverage is limited to the recorded inputs and ordinary-text encoding mode. |
| `results/language_mix.json` | Four quota checks and three hypothetical sampling settings. | Does not measure real corpus quality or identify an optimal German/Spanish ratio. |
| [Corpus pilot](../results/quota_pilot.json) | On PUD test sentences, 75:25 versus 90:10 reduced equal-language byte perplexity by 1.63%. Spanish fell 4.25% and German rose 1.05%. The 50:50 reference had the lowest aggregate point estimate. | Perplexity applies to a statistical bigram model. Task accuracy and performance of neural language models require separate evaluation. |
| Report source annotations | 19 source blocks and 184 displayed execution lines at the pinned MinBPE version. | Documents analysis of upstream code, rather than a newly authored BPE algorithm. |
| Three figures | Two diagrams derived from an executed controlled example; one mathematical sampling scenario. | Does not measure downstream model performance. |

The text `abababab` produces sequence lengths 8, 4, 2, and 1 through three learned merges; its vocabulary grows from 256 to 259 entries. The assumed inventory ratio German:Spanish = 9:1 yields shares 50:50, 75:25, and 90:10 at exponents 0, 0.5, and 1. The first set describes an executed tokenizer trace; the second describes quota arithmetic.

The report's 5-million-character budget, 8,192-entry vocabulary, three seeds, and 5% comparison threshold are proposed experimental settings. They are not measured improvements or paper-established optima. Smaller follow-up studies are specified in [EXTENSIONS](EXTENSIONS.md).

## Public evidence and attribution

Private identifiers and machine-specific paths are excluded from the public record. Bibliographic researcher names and upstream copyright notices remain as necessary source attribution. Build caches, downloaded encoding data, and compiler logs are excluded from version control.
