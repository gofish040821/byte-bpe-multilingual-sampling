# Contribution and AI-use record

The project owner has confirmed that this is a project they handled. This record documents the work, its supporting artifacts, and the use of upstream software and AI assistance for future experience and CV review.

## Attribution

| Component | Attribution supported by the available record |
| --- | --- |
| BPE implementation in `vendor/minbpe/` | Upstream MinBPE by Andrej Karpathy; fixed commit, original license, and hashes retained. It is not a newly invented or independently reimplemented algorithm in this repository. |
| Walkthroughs, comparison harness, quota calculations, checks and report tooling | Project-specific artifacts generated and revised with Codex assistance. |
| Technical report, source annotations, literature synthesis and experiment proposal | Developed with AI assistance, including delegated evidence checks and revisions. The preserved interaction record describes that assistance. |
| Project scope and presentation requirements | Directed by the project owner, including analysis coverage, explanatory depth, report/figure revisions, and public-repository privacy requirements. |
| Project ownership and involvement | Confirmed directly by the project owner. This confirmation identifies the work as part of their project experience; the upstream and AI-assistance attribution above still applies. |

Recorded successful runs demonstrate behavior of the checked-out project artifacts in the recorded environment. They do not establish who independently implemented the code or reproduced those runs.

## Safe public claims

The repository supports statements that the **project contains** an instrumented BPE walkthrough, a source-level MinBPE analysis, differential checks on eight ordinary-text cases, tested quota calculations, and a documented multilingual sampling proposal. A description can also identify it as an **AI-assisted reproducible tokenization study**.

It does not support claims of a new tokenizer algorithm, improved model accuracy, a trained German/Spanish tokenizer selected through experiments, a proven optimal language ratio, or independent implementation by the project owner.

## Experience interpretation

The work can be presented as an owned, AI-assisted research project covering tokenizer
analysis, source reading, reproducibility, literature synthesis, and experiment
design. The available numerical evidence concerns the executed examples and checks.
Real-corpus ratio experiments remain future work, and the upstream BPE algorithm
is not claimed as a new invention.

For a detailed narrative and an artifact-by-artifact evidence map, read
[PROJECT_EXPERIENCE](PROJECT_EXPERIENCE.md) and the
[structured project record](../experience/project.json).

## Evidence

- [Recorded checks](../results/verification.json)
- [Quota calculations](../results/language_mix.json)
- [AI-interaction excerpts](../reports/content/ai_interaction.json)
- [Full retained interaction record](../reports/content/ai_interaction_full.json)
- [Upstream provenance](../vendor/provenance.json)
- [Suggested CV wording](CV_DESCRIPTIONS.md)
