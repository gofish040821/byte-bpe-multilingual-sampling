# Contribution and AI-use record

The project owner has confirmed that this is a project they handled. This record documents the work, its supporting artifacts, and the use of upstream software and AI assistance for future experience and CV review.

## Attribution

| Component | Attribution supported by the available record |
| --- | --- |
| BPE implementation in `vendor/minbpe/` | Upstream MinBPE by Andrej Karpathy; fixed commit, original license, and hashes retained. It is not a newly invented or independently reimplemented algorithm in this repository. |
| Walkthroughs, comparison harness, quota allocator and report tooling | Project-specific artifacts generated and revised with Codex assistance. |
| Multilingual quota pilot | The owner requested an empirical test of the sampling proposal. The project used Codex assistance to implement, run and document the controlled comparisons. Corpus texts and their credits belong to the upstream sources listed in [REFERENCES](REFERENCES.md). |
| Technical report, source annotations, literature synthesis and experiment proposal | Developed with AI assistance, including delegated evidence checks and revisions. The preserved interaction record describes that assistance. |
| Project scope and presentation requirements | Directed by the project owner, including analysis coverage, explanatory depth, report/figure revisions, and public-repository privacy requirements. |
| Project ownership and involvement | Confirmed directly by the project owner. This confirmation identifies the work as part of their project experience; the upstream and AI-assistance attribution above still applies. |

Recorded successful runs demonstrate behavior of the checked-out project artifacts in the recorded environment. They do not establish who independently implemented the code or reproduced those runs.

## Experience interpretation

The project covers source-level BPE analysis, exact encoding checks on eight inputs, quota implementation, and empirical evaluation of German/Spanish training mixtures. The [pilot results](../results/quota_pilot.json) report language-specific and aggregate scores under a fixed small language model and corpus protocol. A CV claim about perplexity should name the metric, model, comparator and evaluation data. The project includes no task with labeled answers for an accuracy comparison.

For a detailed narrative and an artifact-by-artifact evidence map, read
[PROJECT_EXPERIENCE](PROJECT_EXPERIENCE.md) and the
[structured project record](../experience/project.json).

## Evidence

- [Recorded checks](../results/verification.json)
- [Quota calculations](../results/language_mix.json)
- [Quota-pilot code](../code/quota_pilot.py) and [measured outcomes](../results/quota_pilot.json)
- [AI-interaction excerpts](../reports/content/ai_interaction.json)
- [Full retained interaction record](../reports/content/ai_interaction_full.json)
- [Upstream provenance](../vendor/provenance.json)
- [Suggested CV wording](CV_DESCRIPTIONS.md)
