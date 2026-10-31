"""验证 MinBPE GPT4Tokenizer 与 tiktoken cl100k_base 的普通文本编码。

运行：python code/gpt4_check.py
首次运行需要下载 cl100k_base 分词数据；缓存保留于被 Git 忽略的 .cache/tiktoken。
这里只加载已有分词器，不调用 GPT-4 API，不下载或训练语言模型。
"""

from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(ROOT / ".cache" / "tiktoken"))

import regex  # noqa: E402
import tiktoken  # noqa: E402
from minbpe import GPT4Tokenizer  # noqa: E402

COMMIT = "1acefe89412b20245db5a22d2a02001e547dc602"
SAMPLES = [
    ("英文", "Hello, world!"),
    ("德语", "Füße, Straße und Häuser."),
    ("西班牙语", "¡Hola! ¿Cómo estás? El niño come piña."),
    ("中文", "你好，世界！"),
    ("数字", "1234567890"),
    ("换行", "line one\n\nline two\n"),
    ("Emoji", "🙂🚀"),
    ("空字符串", ""),
]


def safe_piece(raw: bytes) -> dict:
    """一个 token 可能只有半个 UTF-8 字符，所以同时保存原始字节和严格解码结果。"""
    try:
        decoded = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        decoded = None
    return {
        "bytes": list(raw),
        "hex": raw.hex(" "),
        "utf8_text_if_complete": decoded,
        "display": decoded if decoded is not None else "<不完整 UTF-8 字节；需与相邻 token 合并解码>",
    }


def build_results() -> dict:
    reference = tiktoken.get_encoding("cl100k_base")
    reproduced = GPT4Tokenizer()
    cases = []
    for label, text in SAMPLES:
        actual = reproduced.encode(text)
        expected = reference.encode(text)
        decoded = reproduced.decode(actual)
        chunks = regex.findall(reproduced.compiled_pattern, text)
        tokens = []
        for token_id in expected:
            entry = {"token_id": token_id, **safe_piece(reference.decode_single_token_bytes(token_id))}
            tokens.append(entry)
        assert actual == expected, f"{label} 的两种编码不一致"
        assert decoded == text, f"{label} 无法完整解码还原"
        assert "".join(chunks) == text, f"{label} 的预分块没有覆盖完整文本"
        assert b"".join(bytes(item["bytes"]) for item in tokens) == text.encode("utf-8")
        cases.append({
            "label": label,
            "text": text,
            "utf8_bytes": list(text.encode("utf-8")),
            "regex_chunks": chunks,
            "minbpe_ids": actual,
            "tiktoken_ids": expected,
            "token_count": len(actual),
            "tokens": tokens,
            "encoding_equal": actual == expected,
            "decoded_text": decoded,
            "roundtrip_equal": decoded == text,
        })

    shuffle = []
    for byte_value in [32, 65, 97, 98, 10, 228]:
        shuffled = reproduced.byte_shuffle[byte_value]
        restored = reproduced.inverse_byte_shuffle[shuffled]
        assert restored == byte_value
        assert reference.decode_single_token_bytes(shuffled) == bytes([byte_value])
        shuffle.append({
            "raw_byte": byte_value,
            "raw_byte_hex": f"{byte_value:02x}",
            "cl100k_single_byte_token_id": shuffled,
            "inverse_shuffle_byte": restored,
        })

    not_trainable = False
    try:
        reproduced.train("abababab", 259)
    except NotImplementedError:
        not_trainable = True
    assert not_trainable, "固定版本的 GPT4Tokenizer.train 应明确拒绝重新训练"
    assert len(reproduced.byte_shuffle) == 256
    assert len(set(reproduced.byte_shuffle.values())) == 256
    checks = [
        {"name": "8 类普通文本编码与 cl100k_base 一致", "passed": all(row["encoding_equal"] for row in cases)},
        {"name": "8 类普通文本完整往返一致", "passed": all(row["roundtrip_equal"] for row in cases)},
        {"name": "预分块完整覆盖每段输入", "passed": all("".join(row["regex_chunks"]) == row["text"] for row in cases)},
        {"name": "256 个字节编号构成可逆映射", "passed":
         all(reproduced.inverse_byte_shuffle[reproduced.byte_shuffle[b]] == b for b in range(256))},
        {"name": "GPT4Tokenizer.train 明确未实现", "passed": not_trainable},
        {"name": "存在不可单独按 UTF-8 解码的 token", "passed":
         any(token["utf8_text_if_complete"] is None for row in cases for token in row["tokens"])},
    ]
    assert all(row["passed"] for row in checks), checks
    return {
        "metadata": {
            "python": platform.python_version(),
            "minbpe_commit": COMMIT,
            "regex_version": importlib.metadata.version("regex"),
            "tiktoken_version": importlib.metadata.version("tiktoken"),
            "encoding_name": reference.name,
            "random_seed": None,
            "randomness": "无随机步骤；分词不调用生成模型",
            "cache_policy": "TIKTOKEN_CACHE_DIR override or ignored .cache/tiktoken; absolute local path omitted",
        },
        "scope": "只验证该固定版本 MinBPE 对 cl100k_base 普通文本编码的复现；不代表所有 GPT 型号。",
        "limitations": [
            "只测试有限样例，不等于对所有可能文本的形式化证明。",
            "没有训练 GPT-4，也没有调用 GPT-4 生成回答。",
            "不把特殊 token 加入普通文本往返测试；此版本 GPT4Tokenizer.decode 未处理其专用解码分支。",
            "一个 token 的字节未必能单独解码成有效字符；应先拼接完整字节，再进行 UTF-8 解码。",
        ],
        "cases": cases,
        "byte_shuffle_examples": shuffle,
        "checks": checks,
    }


def render_text(result: dict) -> str:
    lines = ["MinBPE 与 cl100k_base 编码核对", result["scope"],
             f"MinBPE 固定提交：{COMMIT}",
             f"tiktoken 版本：{result['metadata']['tiktoken_version']}",
             f"regex 版本：{result['metadata']['regex_version']}", ""]
    for row in result["cases"]:
        lines += [f"【{row['label']}】原文：{row['text']!r}",
                  f"  正则预分块：{row['regex_chunks']!r}",
                  f"  MinBPE ID：{row['minbpe_ids']}",
                  f"  tiktoken ID：{row['tiktoken_ids']}",
                  f"  token 数：{row['token_count']}；编码一致：{row['encoding_equal']}；完整往返：{row['roundtrip_equal']}"]
        for token in row["tokens"]:
            lines.append(f"    ID {token['token_id']}；hex {token['hex']}；显示 {token['display']!r}")
        lines.append("")
    lines += ["字节编号置换：原始字节值不必等于 cl100k_base 的单字节 token ID。"]
    for row in result["byte_shuffle_examples"]:
        lines.append(f"  原始 byte {row['raw_byte']} -> token ID {row['cl100k_single_byte_token_id']}"
                     f" -> 逆映射还原 byte {row['inverse_shuffle_byte']}")
    lines += ["", "检查结果："]
    lines.extend(f"  [{'通过' if row['passed'] else '失败'}] {row['name']}" for row in result["checks"])
    lines += ["", "范围与局限：", *[f"  {item}" for item in result["limitations"]]]
    return "\n".join(lines) + "\n"


def write_results(result: dict) -> None:
    output = ROOT / "results"
    output.mkdir(parents=True, exist_ok=True)
    (output / "gpt4_check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "gpt4_check_zh.txt").write_text(render_text(result), encoding="utf-8")


def main() -> dict:
    result = build_results()
    write_results(result)
    print("cl100k_base comparison: 8 cases and all 6 checks passed.")
    print(f"Results: {ROOT / 'results' / 'gpt4_check.json'}")
    return result


if __name__ == "__main__":
    main()
