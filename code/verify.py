"""重新运行 两项实验，并执行额外的关键行为检查。

运行：python code/verify.py
所有正式结果都会重新生成；不依赖 pytest，也不依赖当前工作目录。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpe_walkthrough  # noqa: E402
import gpt4_check  # noqa: E402
from minbpe.base import get_stats, merge  # noqa: E402


def main() -> dict:
    bpe = bpe_walkthrough.main()
    gpt4 = gpt4_check.main()
    extra = []

    # 多个独立案例检查“相邻对统计可重叠、替换不可重叠”。
    assert get_stats([1, 1, 1, 1]) == {(1, 1): 3}
    assert merge([1, 1, 1, 1], (1, 1), 9) == [9, 9]
    assert merge([1, 2, 1, 2, 1], (1, 2), 9) == [9, 9, 1]
    assert merge([], (1, 2), 9) == []
    extra.append({"name": "重叠、尾部剩余及空序列合并", "passed": True})

    assert [(row["chosen_frequency"], row["non_overlapping_replacements"])
            for row in bpe["training"]["steps"]] == [(4, 4), (3, 2), (1, 1)]
    extra.append({"name": "主例三轮频率及实际替换次数分别为 (4,4)/(3,2)/(1,1)", "passed": True})

    # 错把频率当编码优先级会产生不同结果，此断言确保教学反例确实有区分力。
    bad_ids = list("abcbcbcbc".encode("utf-8"))
    bad_ids = merge(bad_ids, (98, 99), 257)
    assert bad_ids == [97, 257, 257, 257, 257]
    assert bad_ids != bpe["rank_vs_frequency"]["final_ids"]
    extra.append({"name": "按新文本频率先合并的错误算法确实得到不同编码", "passed": True})

    by_label = {row["label"]: row for row in gpt4["cases"]}
    assert by_label["英文"]["minbpe_ids"] == [9906, 11, 1917, 0]
    assert by_label["数字"]["regex_chunks"] == ["123", "456", "789", "0"]
    assert by_label["空字符串"]["minbpe_ids"] == []
    extra.append({"name": "英文已知编码、数字预分块及空文本", "passed": True})

    all_checks = bpe["checks"] + gpt4["checks"] + extra
    assert all(row["passed"] for row in all_checks)
    source_hashes = {}
    for name in ("base.py", "basic.py", "regex.py", "gpt4.py", "__init__.py"):
        data = (ROOT / "vendor" / "minbpe" / name).read_bytes()
        source_hashes[name] = hashlib.sha256(data).hexdigest()
    result = {
        "all_passed": True,
        "check_count": len(all_checks),
        "gpt4_sample_count": len(gpt4["cases"]),
        "checks": all_checks,
        "source_commit": bpe_walkthrough.COMMIT,
        "vendor_file_sha256": source_hashes,
        "note": "哈希记录本次实际读取的 vendor 文件，便于核对；不是自动与远端进行真实性认证。",
        "scope": "检查 BPE 合并机制及 cl100k_base 编码；多语言部分仅验证配额计算，不包含真实语料训练。",
    }
    output = ROOT / "results"
    (output / "verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"检查：{len(all_checks)} 项全部通过。", result["scope"],
             f"cl100k_base 对照样例：{len(gpt4['cases'])} 类。", ""]
    lines += [f"[通过] {row['name']}" for row in all_checks]
    (output / "verification_zh.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Verification: all {len(all_checks)} checks passed.")
    return result


if __name__ == "__main__":
    main()
