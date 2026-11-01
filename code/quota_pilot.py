"""Compare three tokenizer training quotas on German and Spanish held-out text."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
from hashlib import sha256
from io import StringIO
import json
from math import fsum, log2
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from typing import NamedTuple
import unicodedata
from urllib.request import urlopen

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from minbpe.regex import RegexTokenizer
from byte_likelihood import ByteBigramLikelihood
from language_mix import allocate

LANGS = ("de", "es")
ALPHAS = (0.0, 0.5, 1.0)
SEEDS = (11, 29, 47)
BUDGET, TRAIN_SENTENCES, VOCAB = 50_000, 1_500, 512
EOS, BOS, SMOOTH = VOCAB, VOCAB + 1, 0.1
# Isolated newline separators cannot form merges spanning sampled sentences.
PATTERN = r"\n| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|[^\S\n]+"
DESIGN_INVENTORY = {"de": 9, "es": 1}
SOURCE_PINS = (
    ("German-GSD", "de_gsd-ud-train.conllu", "d47d56779e81203ec7a9e3460c7f5afa9f711269",
     "cb1326edce0e4f61847416235611ae6a15d0fed9c8e403c355a1edd9a23b2c77", "4.0"),
    ("Spanish-GSD", "es_gsd-ud-train.conllu", "de16cd88598b302a9a5dab502e10d667458072f7",
     "81af0ef69a5ec0f9a8b37352057d06fd27a66f1e13f7d926562ea1ff5c335fdb", "4.0"),
    ("German-PUD", "de_pud-ud-test.conllu", "38815149e93d35ec81ffa6a941111dcfe39977f4",
     "51e16418c8ca5ff9d14d457eb67f6f051280e7766b3cecc556479d0e42cd73bc", "3.0"),
    ("Spanish-PUD", "es_pud-ud-test.conllu", "4a5fc2b4b4cbe335870836d505cd25a16a24f6ac",
     "4c143cbf4ea9debebc94659a1fcee516e0de2ceba342ac943df3582f333f56de", "3.0"),
)


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    file = NamedTemporaryFile(dir=path.parent, delete=False)
    tmp = Path(file.name)
    try:
        with file as f:
            f.write(data)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def digest(items):
    """SHA-256 of deterministic newline-separated UTF-8 identifiers."""
    return sha256("\n".join(items).encode()).hexdigest()


class Sentence(NamedTuple):
    sid: str
    doc: str
    text: str


def read_sentences(data):
    rows = []
    doc = sid = ""
    for line in data.decode("utf-8-sig").splitlines():
        if line.startswith("# newdoc id = "):
            doc = line.removeprefix("# newdoc id = ")
        elif line.startswith("# sent_id = "):
            sid = line.removeprefix("# sent_id = ")
        elif line.startswith("# text = "):
            text = unicodedata.normalize("NFC", line.removeprefix("# text = ").strip())
            if not text or not sid:
                raise ValueError("Missing sentence ID or empty text")
            rows.append(Sentence(sid, doc, text))
            sid = ""
    if len({s.sid for s in rows}) != len(rows):
        raise ValueError("Nonunique source sentence ID")
    return rows


def load_corpora(cache_dir, offline):
    sources, train, test = [], {}, {}
    for repo, name, revision, expected, license_version in SOURCE_PINS:
        url = f"https://raw.githubusercontent.com/UniversalDependencies/UD_{repo}/{revision}/{name}"
        target = cache_dir / name
        if target.is_file():
            data = target.read_bytes()
        elif offline:
            raise FileNotFoundError(f"Missing cached {name}; run once without --offline.")
        else:
            with urlopen(url, timeout=90) as response:
                data = response.read()
        if sha256(data).hexdigest() != expected:
            raise ValueError(f"SHA-256 mismatch for {name}")
        if not target.is_file():
            atomic_write(target, data)
        split = train if "-train." in name else test
        rows = split[name[:2]] = read_sentences(data)
        sources.append(dict(treebank=repo, release="UD r2.15", url=url, revision=revision,
                            sha256=expected, license=f"CC BY-SA {license_version}",
                            license_url=url.rsplit("/", 1)[0] + "/LICENSE.txt", sentences=len(rows)))
    aligned = [(s.sid, s.doc) for s in test["de"]]
    if aligned != [(s.sid, s.doc) for s in test["es"]] or len(aligned) != 1000:
        raise ValueError("PUD sentence/document alignment failed")
    if any(not doc for _, doc in aligned) or len({doc for _, doc in aligned}) != 397:
        raise ValueError("PUD document inventory differs from the pinned corpus")
    heldout_text = {s.text for rows in test.values() for s in rows}
    audit = {}
    for lang, rows in train.items():
        excluded = sum(s.text in heldout_text for s in rows)
        candidates = sorted(rows, key=lambda s: digest(("lm-training", lang, s.sid)))
        unique = {}
        for s in candidates:
            if s.text not in heldout_text:
                unique.setdefault(s.text, s)
        chosen = list(unique.values())[:TRAIN_SENTENCES]
        if len(chosen) != TRAIN_SENTENCES:
            raise ValueError("Insufficient training sentences")
        train[lang] = chosen
        audit[lang] = dict(source_train_sentences=len(rows), train_rows_matching_pud_excluded=excluded,
                           duplicate_train_rows_excluded=len(rows) - excluded - len(unique),
                           training_sentences=len(chosen), training_codepoints=sum(len(s.text) for s in chosen),
                           train_ids_sha256=digest(s.sid for s in chosen),
                           test_sentences=len(test[lang]), test_documents=len({s.doc for s in test[lang]}),
                           test_ids_sha256=digest(s.sid for s in test[lang]))
    return sources, audit, train, test


def sample_quota(pool, quota):
    """Fill a character quota with distinct whole sentences in seeded order."""
    selected, remaining = [], quota
    index = 0
    while remaining > 1000 and len(pool[index].text) <= remaining:
        selected.append(pool[index])
        remaining -= len(pool[index].text)
        index += 1
    # Near the boundary, use a subset sum so all treatments have the exact
    # same budget without cutting the final sentence or sampling with replacement.
    parents = {0: None}
    for s in pool[index:]:
        length = len(s.text)
        for previous in list(parents):
            new = previous + length
            if new <= remaining and new not in parents:
                parents[new] = (previous, s)
        if remaining in parents:
            while remaining:
                remaining, s = parents[remaining]
                selected.append(s)
            return selected
    raise ValueError("The exact quota cannot be filled using the available sentences")


def run_condition(seed, alpha, train, test):
    quotas = allocate(DESIGN_INVENTORY, alpha, BUDGET)["character_quotas"]
    samples = {}
    for lang in LANGS:
        order = sorted(train[lang], key=lambda s: digest((str(seed), lang, s.sid)))
        samples[lang] = sample_quota(order, quotas[lang])
    mixed = [(lang, s) for lang in LANGS for s in samples[lang]]
    mixed.sort(key=lambda item: digest(("interleave", str(seed), item[0], item[1].sid)))
    tokenizer = RegexTokenizer(pattern=PATTERN)
    tokenizer.train("\n".join(s.text for _, s in mixed), VOCAB)
    transitions, contexts = Counter(), Counter()
    for lang in LANGS:
        for s in train[lang]:
            ids = tokenizer.encode_ordinary(s.text)
            if tokenizer.decode(ids) != s.text:
                raise ValueError("Training text did not round-trip")
            transitions.update(zip([BOS, *ids], [*ids, EOS]))
            contexts.update([BOS, *ids])

    def logp(previous, token):
        return log2((transitions[previous, token] + SMOOTH) /
                    (contexts[previous] + (VOCAB + 1) * SMOOTH))

    scorer = ByteBigramLikelihood(tokenizer.vocab, BOS, EOS, logp)
    result, documents = {}, []
    training_audit = {}
    for lang in LANGS:
        byte_counts, marginal, canonical = Counter(), defaultdict(list), []
        token_count = 0
        for s in test[lang]:
            raw = s.text.encode()
            ids = tokenizer.encode_ordinary(s.text)
            if tokenizer.decode(ids) != s.text:
                raise ValueError("Held-out text did not round-trip")
            bits = scorer.bits(raw)
            path_bits = -fsum(logp(i, j) for i, j in zip([BOS, *ids], [*ids, EOS]))
            if not 0 <= bits <= path_bits + 1e-8:
                raise ValueError("Marginal cost must not exceed a single-path cost")
            marginal[s.doc].append(bits)
            byte_counts[s.doc] += len(raw)
            canonical.append(path_bits)
            token_count += len(ids)
        byte_count = sum(byte_counts.values())
        total_bits = fsum(fsum(bits) for bits in marginal.values())
        bpb = total_bits / byte_count
        canonical_bpb = fsum(canonical) / byte_count
        result[lang] = dict(test_bytes=byte_count, test_tokens=token_count, exact_bits=total_bits,
                            exact_bpb=bpb, exact_byte_ppl=2 ** bpb, canonical_bpb=canonical_bpb,
                            canonical_byte_ppl=2 ** canonical_bpb)
        documents.extend((seed, alpha, lang, doc, byte_counts[doc], fsum(marginal[doc]))
                         for doc in sorted(marginal))
        count = sum(len(s.text) for s in samples[lang])
        if count != quotas[lang]:
            raise ValueError("Tokenizer quota mismatch")
        training_audit[lang] = dict(sentences=len(samples[lang]), codepoints=count,
                                    ids_sha256=digest(s.sid for s in samples[lang]))
    macro_bpb = fsum(result[lang]["exact_bpb"] for lang in LANGS) / len(LANGS)
    merges_hash = digest(f"{a},{b},{c}" for (a, b), c in tokenizer.merges.items())
    return (dict(seed=seed, alpha=alpha, tokenizer_sample=training_audit, merge_rules_sha256=merges_hash,
                 test=result, macro_exact_bpb=macro_bpb, macro_exact_byte_ppl=2 ** macro_bpb), documents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use previously downloaded, hash-checked corpora.")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache" / "quota-pilot")
    parser.add_argument("--jobs", type=int, default=3, choices=range(1, 10), metavar="1..9")
    args = parser.parse_args()
    sources, split_audit, train, test = load_corpora(args.cache_dir, args.offline)
    with ProcessPoolExecutor(max_workers=args.jobs) as workers:
        futures = [workers.submit(run_condition, seed, alpha, train, test) for seed in SEEDS for alpha in ALPHAS]
        outputs = [f.result() for f in futures]
    runs = [result for result, _ in outputs]
    summary = []
    for alpha in ALPHAS:
        group = [r for r in runs if r["alpha"] == alpha]
        bpb = {lang: fsum(r["test"][lang]["exact_bpb"] for r in group) / len(group) for lang in LANGS}
        bpb["macro"] = fsum(bpb.values()) / len(LANGS)
        summary.append(dict(alpha=alpha, seed_mean_exact_bpb=bpb,
                            exact_byte_ppl={key: 2 ** value for key, value in bpb.items()}))
    record = dict(sources=sources, split_audit=split_audit, protocol={
        "training": "Fixed GSD train sample per language, ordered by the hash of sentence ID with language and lm-training salt. Exclude duplicate NFC text and exact overlaps with either evaluation language. Use the entire fixed sample for each bilingual bigram.",
        "evaluation": "All 1000 official PUD test sentence pairs in 397 aligned source documents. No PUD fitting, model selection or hyperparameter tuning.",
        "tokenizer": "Vendored RegexTokenizer, seeded whole-sentence subsets without replacement, exact character quotas. Newline separators are isolated and never merged.",
        "regex": PATTERN, "nfc_codepoint_budget": BUDGET, "vocab_size": VOCAB, "training_sentences_per_language": TRAIN_SENTENCES,
        "quota_weights_for_design_only": DESIGN_INVENTORY, "alphas": ALPHAS, "paired_seeds": SEEDS,
        "lm": "Additive token bigram on each sentence's deterministic BPE encoding; single BOS context, outcomes = 512 token IDs + EOS.",
        "smoothing_pseudocount": SMOOTH,
        "primary_metric": "Exact probability sums all token paths emitting each UTF-8 string and then EOS. Divide total negative log2 probability by original UTF-8 bytes. Byte perplexity = 2^BPB. Average BPB equally across languages and seeds before exponentiating.",
        "secondary_metric": "Canonical BPB uses only the deterministic BPE path and EOS.",
        "primary_contrast": "75:25 smoothed versus 90:10 proportional under design inventory 9:1. Include 50:50 as equal-share reference.",
        "limits": "A small count model, two languages, two GSD training treebanks, two PUD evaluation treebanks and three tokenizer sampling seeds. Results apply to these test sets. Neural-model quality and task accuracy were not evaluated."
    }, runs=runs, summary=summary)
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["seed", "alpha", "language", "doc_id", "bytes", "bits"])
    for _, documents in outputs:
        writer.writerows(documents)
    csv_data = stream.getvalue().encode()
    record["document_scores"] = dict(path="results/quota_pilot_documents.csv", sha256=sha256(csv_data).hexdigest())
    atomic_write(ROOT / record["document_scores"]["path"], csv_data)
    atomic_write(ROOT / "results/quota_pilot.json", (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
