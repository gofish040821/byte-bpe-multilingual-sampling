# Sources and reuse

`vendor/minbpe/` contains unchanged upstream source from
[karpathy/minbpe](https://github.com/karpathy/minbpe) at commit
`1acefe89412b20245db5a22d2a02001e547dc602`.
The original [MIT license](vendor/LICENSE) and [file provenance](vendor/provenance.json)
are retained. The upstream algorithm and implementation are not claimed as original work.

`regex` and `tiktoken` are installed dependencies, not project-authored libraries.
The `cl100k_base` vocabulary is downloaded at runtime into an ignored cache;
the downloaded vocabulary is not part of the public project files.

The quota pilot reads four Universal Dependencies r2.15 treebanks. The German
and Spanish GSD training data are distributed under CC BY-SA 4.0. The German
and Spanish PUD evaluation data are distributed under CC BY-SA 3.0. The pilot
downloads the upstream files into a local cache. This repository publishes the
experiment code, source identifiers and numerical outputs. See the
[versioned dataset references and author credits](docs/REFERENCES.md#pilot-corpora).

Project-specific wrappers, figures, documentation, and report were produced with
AI assistance. See [contribution provenance](docs/CONTRIBUTIONS.md).
A license for these project-specific materials has not yet been selected;
the upstream MIT license applies to the vendored MinBPE files only.
