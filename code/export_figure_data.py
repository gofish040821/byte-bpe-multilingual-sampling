"""仅使用 Python 标准库，导出三张原生 LaTeX 图所依据的七份数据表。

运行：python code/export_figure_data.py
核对与现有数据逐字节一致后再写入：python code/export_figure_data.py --verify-existing

不导入 Matplotlib/NumPy，不创建或修改图片，也不调用 LaTeX 编译器。
BPE 数据来自真实运行记录；语言抽样数据来自明确标注的 9:1 数学情景。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
SOURCE = ROOT / "results" / "bpe_walkthrough.json"


def json_bytes(content) -> bytes:
    """使用固定 LF 换行，保证 Windows/Linux 导出的数据哈希一致。"""
    text = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
    return text.encode("utf-8")


def csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def source_stages(run: dict) -> list[dict]:
    """以真实 token 字节内容重建每层覆盖区间，不从图形尺寸反推数据。"""
    train = run["training"]
    assert train["official_merges_equal"]
    assert train["text"] == "abababab" and train["vocab_size"] == 259
    vocab = {idx: bytes([idx]) for idx in range(256)}
    records = [(0, train["initial_ids"], train["initial_vocab_size"])]
    for step in train["steps"]:
        pair = step["chosen_pair"]
        raw = bytes(step["new_token_bytes"])
        assert raw == vocab[pair[0]] + vocab[pair[1]]
        vocab[step["new_token_id"]] = raw
        records.append((step["round"], step["after_ids"],
                        train["initial_vocab_size"] + step["round"]))
    original = train["text"].encode("utf-8")
    stages = []
    for stage, ids, vocab_size in records:
        start = 0
        tokens = []
        for token_index, token_id in enumerate(ids):
            raw = vocab[token_id]
            end = start + len(raw)
            assert original[start:end] == raw
            tokens.append({
                "stage": stage,
                "token_index_1based": token_index + 1,
                "token_id": token_id,
                "token_text": raw.decode("utf-8"),
                "start_byte_0based": start,
                "end_byte_exclusive": end,
                "byte_length": len(raw),
                "sequence_token_count": len(ids),
                "vocab_size": vocab_size,
            })
            start = end
        assert start == len(original)
        stages.append({"stage": stage, "token_count": len(ids),
                       "vocab_size": vocab_size, "tokens": tokens})
    assert [row["token_count"] for row in stages] == [8, 4, 2, 1]
    assert [row["vocab_size"] for row in stages] == [256, 257, 258, 259]
    return stages


def overlap_rows(run: dict) -> tuple[list[dict], dict]:
    step = run["training"]["steps"][1]
    ids = step["before_ids"]
    pair = step["chosen_pair"]
    assert ids == [256, 256, 256, 256] and pair == [256, 256]
    selected = set()
    merged = []
    index = 0
    while index < len(ids):
        if ids[index:index + 2] == pair:
            selected.add(index)
            merged.append(step["new_token_id"])
            index += 2
        else:
            merged.append(ids[index])
            index += 1
    rows = [{
        "window": i + 1,
        "left_position_1based": i + 1,
        "right_position_1based": i + 2,
        "left_id": ids[i],
        "right_id": ids[i + 1],
        "included_in_pair_count": ids[i:i + 2] == pair,
        "selected_for_left_to_right_replacement": i in selected,
    } for i in range(len(ids) - 1)]
    assert sum(row["included_in_pair_count"] for row in rows) == step["chosen_frequency"] == 3
    assert len(selected) == step["non_overlapping_replacements"] == 2
    assert merged == step["after_ids"] == [257, 257]
    return rows, step


def sampling_rows() -> list[dict]:
    """9:1 是假设库存比例；输出不衡量 tokenizer 或语言模型的性能。"""
    rows = []
    for i in range(101):
        alpha = i / 100.0
        weight = 9.0 ** alpha
        german = weight / (weight + 1.0) * 100.0
        spanish = 100.0 - german
        assert math.isclose(german + spanish, 100.0, abs_tol=1e-12)
        assert math.isclose(german / spanish, weight, abs_tol=1e-12)
        rows.append({
            "alpha": round(alpha, 2),
            "german_share_pct": round(german, 8),
            "spanish_share_pct": round(spanish, 8),
            "inventory_ratio_german_to_spanish": "9:1",
            "data_kind": "mathematical_scenario_not_performance_measurement",
        })
    assert [rows[i]["german_share_pct"] for i in (0, 50, 100)] == [50.0, 75.0, 90.0]
    assert all(a["german_share_pct"] < b["german_share_pct"] for a, b in zip(rows, rows[1:]))
    return rows


def build_artifacts(run: dict) -> dict[str, bytes]:
    stages = source_stages(run)
    bpe = [token for stage in stages for token in stage["tokens"]]
    windows, step = overlap_rows(run)
    sampling = sampling_rows()
    key_rows = [sampling[i] for i in (0, 50, 100)]
    return {
        "bpe_merges.csv": csv_bytes(bpe),
        "bpe_merges_data.json": json_bytes({
            "source": "results/bpe_walkthrough.json#training",
            "text": run["training"]["text"], "stages": stages,
            "scope": run["scope"],
        }),
        "overlap.csv": csv_bytes(windows),
        "overlap_data.json": json_bytes({
            "source": "results/bpe_walkthrough.json#training.steps[1]",
            "windows": windows, "input_ids": step["before_ids"],
            "pair_count": step["chosen_frequency"],
            "actual_replacements": step["non_overlapping_replacements"],
            "output_ids": step["after_ids"],
        }),
        "language_sampling.csv": csv_bytes(sampling),
        "language_sampling_key_points.csv": csv_bytes(key_rows),
        "language_sampling_data.json": json_bytes({
            "formula": "p_i = n_i**alpha / sum_j(n_j**alpha)",
            "assumptions": {"german_inventory": 9, "spanish_inventory": 1,
                            "inventory_unit": "same character-count unit", "alpha_range": [0, 1]},
            "key_points": key_rows, "curve_points": sampling,
            "scope": "根据假设计算的数学情景，不是分词效率或语言模型性能的实测结果。",
        }),
    }


def update_data_audit(artifacts: dict[str, bytes], run: dict, prior_equal: bool) -> dict:
    """只更新数据来源和审计字段；保留原生 LaTeX 渲染及导出检查记录。"""
    manifest_file = OUT / "manifest.json"
    manifest = json.loads(manifest_file.read_text("utf-8")) if manifest_file.exists() else {}
    audit = []
    for name, data in artifacts.items():
        entry = {"path": f"figures/{name}", "sha256": hashlib.sha256(data).hexdigest()}
        if name.endswith(".csv"):
            rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
            entry["row_count"] = len(rows)
            if name.startswith("language_sampling"):
                entry["formula_rechecked"] = True
        audit.append(entry)
    manifest.update({
        "source_file": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "source_hash_encoding": "UTF-8 text with LF line endings",
        "minbpe_commit": run["metadata"]["minbpe_commit"],
        "source_data_checked": True,
        "data_audit": audit,
        "data_table_generation": "code/export_figure_data.py (Python standard library only; native figures are rendered from the LaTeX sources listed for each figure).",
        "data_export_verification": {
            "file_count": len(artifacts),
            "all_preexisting_files_byte_identical": prior_equal,
            "checks": ["BPE token byte intervals and source merges agree",
                       "Three overlapping windows produce two non-overlapping replacements",
                       "101 sampling points agree with the 9:1 scenario formula",
                       "Key German shares are 50%, 75%, 90%; each language pair sums to 100%"],
        },
    })
    manifest_file.write_bytes(json_bytes(manifest))
    return manifest["data_export_verification"]


def main(verify_existing: bool = False) -> dict:
    run = json.loads(SOURCE.read_text("utf-8"))
    artifacts = build_artifacts(run)
    mismatches = [name for name, data in artifacts.items()
                  if not (OUT / name).exists() or (OUT / name).read_bytes() != data]
    if verify_existing and mismatches:
        raise AssertionError("Existing data differs; no output overwritten: " + ", ".join(mismatches))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in artifacts.items():
        (OUT / name).write_bytes(data)
    verification = update_data_audit(artifacts, run, prior_equal=not mismatches)
    print("Exported 7 source tables using only the Python standard library.")
    print("Existing tables byte-identical:", not mismatches)
    return verification


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-existing", action="store_true",
                        help="Require all seven existing files to match before writing.")
    args = parser.parse_args()
    main(verify_existing=args.verify_existing)
