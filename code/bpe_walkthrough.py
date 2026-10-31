"""逐步演示字节级 BPE，并与固定版本 MinBPE 的真实结果核对。

运行：python code/bpe_walkthrough.py
无需 GPU，也不训练语言模型。结果写到本项目 results 目录。
"""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from minbpe import BasicTokenizer  # noqa: E402
from minbpe.base import get_stats, merge  # noqa: E402

COMMIT = "1acefe89412b20245db5a22d2a02001e547dc602"


def metadata() -> dict:
    """保存环境信息；本演示不使用随机数，不存在需要设置的随机种子。"""
    return {
        "python": platform.python_version(),
        "minbpe_commit": COMMIT,
        "regex_version": importlib.metadata.version("regex"),
        "tiktoken_version": importlib.metadata.version("tiktoken"),
        "random_seed": None,
        "randomness": "无随机步骤；结果由文本、代码和合并规则确定",
    }


def pieces(ids: list[int], vocab: dict[int, bytes]) -> list[str]:
    """仅用于展示；不能用单个 token 的显示文本替代其真实字节。"""
    return [vocab[idx].decode("utf-8", errors="replace") for idx in ids]


def pair_table(stats: dict, vocab: dict[int, bytes], merges: dict | None = None) -> list:
    rows = []
    for pair, count in stats.items():
        row = {"pair": list(pair), "pieces": pieces(list(pair), vocab), "count": count}
        if merges is not None:
            row["merge_rank"] = merges.get(pair)  # null 表示词表没有这条合并规则。
        rows.append(row)
    return rows


def trace_training(text: str, vocab_size: int) -> tuple[dict, dict, dict]:
    """复现 BasicTokenizer.train 的步骤，直接调用官方统计和合并函数。"""
    ids = list(text.encode("utf-8"))
    vocab = {idx: bytes([idx]) for idx in range(256)}
    merges = {}
    steps = []
    initial_ids = ids.copy()
    for i in range(vocab_size - 256):
        stats = get_stats(ids)
        if not stats:
            raise ValueError("语料已没有相邻对；请减少目标词表大小。")
        # Python 字典保留插入顺序；并列最多时，max 选择首次出现的那一对。
        pair = max(stats, key=stats.get)
        new_id = 256 + i
        before = ids.copy()
        row = {
            "round": i + 1,
            "before_ids": before,
            "before_pieces": pieces(before, vocab),
            "all_pair_counts": pair_table(stats, vocab),
            "chosen_pair": list(pair),
            "chosen_frequency": stats[pair],
            "new_token_id": new_id,
        }
        ids = merge(ids, pair, new_id)
        merges[pair] = new_id
        vocab[new_id] = vocab[pair[0]] + vocab[pair[1]]
        row.update({
            "non_overlapping_replacements": len(before) - len(ids),
            "new_token_bytes": list(vocab[new_id]),
            "new_token_text": vocab[new_id].decode("utf-8", errors="replace"),
            "after_ids": ids.copy(),
            "after_pieces": pieces(ids, vocab),
        })
        steps.append(row)
    official = BasicTokenizer()
    official.train(text, vocab_size)
    assert merges == official.merges, "逐步记录的合并规则与官方实现不一致"
    assert vocab == official.vocab, "逐步记录的词表与官方实现不一致"
    assert ids == official.encode(text), "主例最终序列与官方编码不一致"
    result = {
        "text": text,
        "vocab_size": vocab_size,
        "initial_ids": initial_ids,
        "initial_vocab_size": 256,
        "steps": steps,
        "final_ids": ids,
        "official_final_ids": official.encode(text),
        "official_merges_equal": merges == official.merges,
        "roundtrip_text": official.decode(official.encode(text)),
    }
    return result, merges, vocab


def trace_encoding(text: str, tokenizer: BasicTokenizer) -> dict:
    """编码只使用已有规则，选最早学到的可用规则，不按新文本频率重学。"""
    ids = list(text.encode("utf-8"))
    initial = ids.copy()
    steps = []
    while len(ids) >= 2:
        stats = get_stats(ids)
        pair = min(stats, key=lambda item: tokenizer.merges.get(item, float("inf")))
        if pair not in tokenizer.merges:
            break
        before = ids.copy()
        new_id = tokenizer.merges[pair]
        ids = merge(ids, pair, new_id)
        steps.append({
            "round": len(steps) + 1,
            "before_ids": before,
            "before_pieces": pieces(before, tokenizer.vocab),
            "all_pair_counts": pair_table(stats, tokenizer.vocab, tokenizer.merges),
            "chosen_pair": list(pair),
            "chosen_frequency": stats[pair],
            "chosen_rank": new_id,
            "non_overlapping_replacements": len(before) - len(ids),
            "after_ids": ids.copy(),
            "after_pieces": pieces(ids, tokenizer.vocab),
        })
    expected = tokenizer.encode(text)
    assert ids == expected, "编码步骤与官方 encode 不一致"
    assert tokenizer.decode(ids) == text, "完整 token 序列无法还原输入"
    return {
        "text": text,
        "initial_ids": initial,
        "steps": steps,
        "final_ids": ids,
        "final_pieces": pieces(ids, tokenizer.vocab),
        "official_final_ids": expected,
        "roundtrip_text": tokenizer.decode(ids),
        "stop_reason": "没有更多可用的已学合并规则，或序列长度小于 2",
    }


def build_results() -> dict:
    training, _, _ = trace_training("abababab", 259)
    toy = BasicTokenizer()
    toy.train("abababab", 259)
    encoding = trace_encoding("ababab", toy)

    # 这个独立语料产生 ab -> 256、bc -> 257，用真实训练结果说明 rank 的作用。
    counter = BasicTokenizer()
    counter.train("ab1ab2ab3ab4bcbcbc", 258)
    assert counter.merges == {(97, 98): 256, (98, 99): 257}
    counter_trace = trace_encoding("abcbcbcbc", counter)
    counter_trace["training_text"] = "ab1ab2ab3ab4bcbcbc"
    counter_trace["learned_rules"] = [
        {"pair": list(pair), "id": idx, "text": counter.vocab[idx].decode("utf-8")}
        for pair, idx in counter.merges.items()
    ]
    counter_trace["explanation"] = (
        "新文本中 ab 出现 1 次、bc 出现 4 次；编码仍先合并 rank 为 256 的 ab，"
        "不是先合并更频繁但 rank 为 257 的 bc。"
    )

    overlap_ids = [97, 97, 97]
    overlap_stats = get_stats(overlap_ids)
    overlap_output = merge(overlap_ids, (97, 97), 256)
    unicode_rows = []
    for text in ("你好", "é", "🙂", "你好，España! 🙂"):
        ids = toy.encode(text)
        decoded = toy.decode(ids)
        assert decoded == text
        unicode_rows.append({
            "text": text,
            "unicode_character_count": len(text),
            "utf8_bytes": list(text.encode("utf-8")),
            "utf8_byte_count": len(text.encode("utf-8")),
            "token_ids": ids,
            "decoded": decoded,
            "roundtrip_equal": decoded == text,
        })

    checks = [
        {"name": "训练结果与官方 train/encode 一致", "passed": training["official_merges_equal"]},
        {"name": "训练最终编码为 [258]", "passed": training["final_ids"] == [258]},
        {"name": "新文本编码为 [257, 256]", "passed": encoding["final_ids"] == [257, 256]},
        {"name": "重叠 pair 计数 2，但实际只替换 1 次", "passed":
         overlap_stats[(97, 97)] == 2 and overlap_output == [256, 97]},
        {"name": "空文本可编码并还原", "passed": toy.encode("") == [] and toy.decode([]) == ""},
        {"name": "Unicode 完整序列往返一致", "passed": all(row["roundtrip_equal"] for row in unicode_rows)},
        {"name": "编码优先级不等于新文本 pair 频率", "passed":
         counter_trace["steps"][0]["chosen_pair"] == [97, 98]
         and counter_trace["final_ids"] == [256, 99, 257, 257, 257]},
    ]
    assert all(row["passed"] for row in checks), checks
    return {
        "metadata": metadata(),
        "scope": "机制分析用微型字节级 BPE；不是训练 GPT-4，也不代表 cl100k_base 的真实切分。",
        "training": training,
        "encoding_new_text": encoding,
        "overlap_example": {
            "text": "aaa", "input_ids": overlap_ids,
            "pair": [97, 97], "pair_count": overlap_stats[(97, 97)],
            "output_ids": overlap_output,
            "actual_replacements": len(overlap_ids) - len(overlap_output),
        },
        "unicode_examples": unicode_rows,
        "rank_vs_frequency": counter_trace,
        "checks": checks,
    }


def render_text(result: dict) -> str:
    lines = ["BPE 逐步演示", result["scope"],
             f"MinBPE 固定提交：{COMMIT}", "本实验没有随机步骤。", "",
             "一、训练：abababab，词表大小 259 = 256 个基础字节 + 3 次合并"]
    for row in result["training"]["steps"]:
        lines += [f"第 {row['round']} 轮：",
                  f"  合并前 ID：{row['before_ids']}",
                  f"  合并前片段：{row['before_pieces']}", "  所有相邻 pair 计数："]
        for pair in row["all_pair_counts"]:
            lines.append(f"    {pair['pair']} {pair['pieces']!r}：{pair['count']} 次")
        lines += [f"  选择：{row['chosen_pair']}；统计频率 {row['chosen_frequency']}",
                  f"  实际非重叠替换：{row['non_overlapping_replacements']} 次",
                  f"  新 ID {row['new_token_id']} = {row['new_token_text']!r}；字节 {row['new_token_bytes']}",
                  f"  合并后 ID：{row['after_ids']}；片段 {row['after_pieces']}", ""]
    lines += ["二、编码新文本：ababab；沿用已有规则，不重新训练"]
    for row in result["encoding_new_text"]["steps"]:
        lines.append(f"  {row['before_ids']} --规则 rank {row['chosen_rank']}--> {row['after_ids']}")
    lines += [f"  完整解码：{result['encoding_new_text']['roundtrip_text']!r}", "",
              "三、重叠计数：aaa 中 aa 有 2 个相邻位置，但一次只能替换 1 对，得到 [256, 97]。", "",
              "四、编码 rank 与频率的反例", result["rank_vs_frequency"]["explanation"],
              f"  训练语料：{result['rank_vs_frequency']['training_text']}",
              f"  新文本：{result['rank_vs_frequency']['text']}",
              f"  最终 ID：{result['rank_vs_frequency']['final_ids']}", "",
              "五、字符不等于字节；完整 token 序列才能可靠解码"]
    for row in result["unicode_examples"]:
        lines.append(f"  {row['text']!r}：{row['unicode_character_count']} 个 Unicode 字符，"
                     f"{row['utf8_byte_count']} 个 UTF-8 字节 {row['utf8_bytes']}；往返一致。")
    lines += ["", "六、断言检查"]
    lines.extend(f"  [{'通过' if row['passed'] else '失败'}] {row['name']}" for row in result["checks"])
    return "\n".join(lines) + "\n"


def write_results(result: dict) -> None:
    output = ROOT / "results"
    output.mkdir(parents=True, exist_ok=True)
    (output / "bpe_walkthrough.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "bpe_walkthrough_zh.txt").write_text(render_text(result), encoding="utf-8")


def main() -> dict:
    result = build_results()
    write_results(result)
    print("BPE walkthrough: all 7 checks passed.")
    print(f"Results: {ROOT / 'results' / 'bpe_walkthrough.json'}")
    return result


if __name__ == "__main__":
    main()
