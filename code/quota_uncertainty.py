"""Paired document bootstrap for the pre-specified 75:25 vs 90:10 contrast."""
import csv
import hashlib
import json
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results/quota_pilot_documents.csv"
OUTPUT = ROOT / "results/quota_uncertainty.json"
SEEDS = (11, 29, 47)
LANGUAGES = ("de", "es")
RESAMPLES = 4000
BOOTSTRAP_SEED = 101


def load_costs(path):
    costs, sizes = {}, {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            seed, alpha = int(row["seed"]), float(row["alpha"])
            language, doc = row["language"], row["doc_id"]
            size, bits = int(row["bytes"]), float(row["bits"])
            key = (doc, language, seed, alpha)
            if key in costs or seed not in SEEDS or alpha not in (0, 0.5, 1) or language not in LANGUAGES:
                raise ValueError(f"Unexpected or duplicate observation: {key}")
            if size <= 0 or not math.isfinite(bits) or bits < 0 or sizes.setdefault((doc, language), size) != size:
                raise ValueError(f"Invalid scores or different test bytes for {key}")
            costs[key] = bits
    docs = sorted({doc for doc, _ in sizes})
    if not docs or len(costs) != len(docs) * len(LANGUAGES) * len(SEEDS) * 3:
        raise ValueError("Incomplete set of matched document scores")
    return docs, sizes, costs


def document_effects(docs, sizes, costs, seeds):
    # A row holds the two byte denominators and the paired change in total bits
    # for the same document. Pool bits and bytes before dividing in each language.
    rows = []
    for doc in docs:
        delta = [sum(costs[doc, lang, seed, 0.5] - costs[doc, lang, seed, 1.0]
                     for seed in seeds) / len(seeds) for lang in LANGUAGES]
        rows.append((sizes[doc, "de"], sizes[doc, "es"], *delta))
    return rows


def relative_changes(rows):
    de_bytes, es_bytes, de_bits, es_bits = map(sum, zip(*rows))
    de, es = de_bits / de_bytes, es_bits / es_bytes
    return {lang: 100 * math.expm1(math.log(2) * rate)
            for lang, rate in zip(("de", "es", "macro"), (de, es, (de + es) / 2))}


def percentile(values, q):
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (position - lo) * (ordered[hi] - ordered[lo])


def main():
    csv_sha = hashlib.sha256(INPUT.read_bytes()).hexdigest()
    pilot = json.loads((ROOT / "results/quota_pilot.json").read_text(encoding="utf-8"))
    if csv_sha != pilot["document_scores"]["sha256"]:
        raise ValueError("Document scores and pilot summary come from different runs")
    docs, sizes, costs = load_costs(INPUT)
    rows = document_effects(docs, sizes, costs, SEEDS)
    point = relative_changes(rows)
    randomizer = random.Random(BOOTSTRAP_SEED)
    draws = [relative_changes(randomizer.choices(rows, k=len(rows))) for _ in range(RESAMPLES)]
    result = {
        "estimand": "100 * (PPL_75:25 / PPL_90:10 - 1); negative favors 75:25",
        "averaging": "Average bits across paired seeds, pool costs by bytes within language, then give German and Spanish equal weight in log space.",
        "resampling_unit": "Aligned PUD source document with replacement; same draw for both languages, all seeds and both quotas.",
        "scope": "Percentile intervals reflect test-document variability conditional on the fitted models, not uncertainty across corpora or model families.",
        "n_documents": len(docs), "replicates": RESAMPLES, "bootstrap_seed": BOOTSTRAP_SEED,
        "input_sha256": csv_sha,
        "point_percent": point,
        "percentile_95_percent": {
            key: [percentile([draw[key] for draw in draws], q) for q in (0.025, 0.975)] for key in point
        },
        "individual_seed_percent": {
            seed: relative_changes(document_effects(docs, sizes, costs, [seed])) for seed in SEEDS
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
