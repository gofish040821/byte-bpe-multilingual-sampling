# Sources and third-party provenance

## Software

### MinBPE

- Repository: [karpathy/minbpe](https://github.com/karpathy/minbpe).
- Pinned commit: [`1acefe89412b20245db5a22d2a02001e547dc602`](https://github.com/karpathy/minbpe/tree/1acefe89412b20245db5a22d2a02001e547dc602).
- The files in [`vendor/minbpe`](../vendor/minbpe) are upstream software. The project-specific walkthroughs call these files; they do not replace their authorship.
- Original license: [MIT license at the pinned commit](https://github.com/karpathy/minbpe/blob/1acefe89412b20245db5a22d2a02001e547dc602/LICENSE). Its notice is retained in [`vendor/LICENSE`](../vendor/LICENSE).
- Retrieval and per-file hashes: [`vendor/provenance.json`](../vendor/provenance.json).

The report's source line numbers refer to this pinned commit, rather than a moving default branch. Its `GPT4Tokenizer` wrapper loads `cl100k_base` rules and recovers merge relationships; it does not train GPT-4 or provide the full GPT-4 model.

### tiktoken

- Repository and usage: [openai/tiktoken](https://github.com/openai/tiktoken).
- License: [upstream MIT license](https://github.com/openai/tiktoken/blob/main/LICENSE). The installed `tiktoken==0.14.0` distribution was also inspected and contains an MIT license notice.
- This project depends on the installed package and compares ordinary-text encodings with `cl100k_base`. It does not vendor the package or model weights.
- Runtime encoding data may be fetched by `tiktoken` when its cache is empty. Cache files are excluded from the public repository. The software-license reference should not be treated as a blanket project-authored license for separately downloaded data.

The public repository has not been granted a new blanket license on behalf of its owner. The retained MinBPE license applies to the vendored upstream files. A reuse-license decision for project-specific code, prose and figures remains to be confirmed; public visibility alone does not select one.

## Research papers used in the report

1. **Zhang et al. (2022). _How Robust is Neural Machine Translation to Language Imbalance in Multilingual Tokenizer Training?_** [Paper](https://arxiv.org/abs/2204.14268), [version used in the report](https://arxiv.org/html/2204.14268v2). This motivates treating tokenizer-training sampling separately from model-training sampling. The reported study is machine translation, primarily uses Unigram with a BPE ablation, and does not establish an optimal German/Spanish byte-level BPE ratio.
2. **Rust et al. (2021). _How Good is Your Tokenizer? On the Monolingual Performance of Multilingual Language Models._** [ACL Anthology](https://aclanthology.org/2021.acl-long.243/). This motivates inspecting language-specific fragmentation, including fertility. Such diagnostics do not by themselves prove downstream quality or make cross-language fertility values directly comparable.
3. **Chung et al. (2023). _UniMax: Fairer and more Effective Language Sampling for Large-Scale Multilingual Pretraining._** [Paper](https://arxiv.org/abs/2304.09151), [version used in the report](https://arxiv.org/html/2304.09151v1). This motivates considering language budgets, a consistent character-counting unit and limits on repeated small-language data. Results from the broader pretraining setup cannot be attributed solely to a tokenizer-mix change.

The German/Spanish experiment design in this project adapts these ideas. The papers are not cited as proof that a 50:50 mix, the proposed budget or a chosen threshold is optimal.

## Measurement in the quota pilot

A text can have several token sequences that decode to the same bytes. The pilot's bigram model permits an exact sum of the probabilities of those sequences, including sentence termination. The resulting negative log likelihood per UTF-8 byte gives all three mixtures a common evaluation unit. The score of the tokenizer's deterministic segmentation is a separate diagnostic. For the distinction between these likelihoods, see [Cao and Rimell (2021), *You should evaluate your language model on marginal likelihood over tokenisations*](https://aclanthology.org/2021.emnlp-main.161/).

## Pilot corpora

The pilot uses the sentence texts from Universal Dependencies release r2.15. Each treebank's pinned README lists its contributors, data sources and license. The GSD files supply training texts. The German and Spanish PUD files provide aligned translations of news and Wikipedia excerpts for testing.

| Treebank | File | Pinned source and credits | License |
| --- | --- | --- | --- |
| German GSD | `de_gsd-ud-train.conllu` | [German GSD README](https://github.com/UniversalDependencies/UD_German-GSD/blob/d47d56779e81203ec7a9e3460c7f5afa9f711269/README.md) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Spanish GSD | `es_gsd-ud-train.conllu` | [Spanish GSD README](https://github.com/UniversalDependencies/UD_Spanish-GSD/blob/de16cd88598b302a9a5dab502e10d667458072f7/README.md) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| German PUD | `de_pud-ud-test.conllu` | [German PUD README](https://github.com/UniversalDependencies/UD_German-PUD/blob/38815149e93d35ec81ffa6a941111dcfe39977f4/README.md) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| Spanish PUD | `es_pud-ud-test.conllu` | [Spanish PUD README](https://github.com/UniversalDependencies/UD_Spanish-PUD/blob/4a5fc2b4b4cbe335870836d505cd25a16a24f6ac/README.md) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |

Training and scoring use normalized sentence text without syntactic annotations. For the preprocessing, sampling and exact upstream file hashes, see the [experiment](../code/quota_pilot.py) and its [run record](../results/quota_pilot.json).

## AI-assisted work

The report was developed with Codex assistance, including delegated literature review and review prompts. Available records describe that actual assistance, rather than claiming that the project owner personally typed every recorded prompt or independently produced the upstream implementation. See [CONTRIBUTIONS.md](CONTRIBUTIONS.md) and the anonymized interaction records with the report sources.
