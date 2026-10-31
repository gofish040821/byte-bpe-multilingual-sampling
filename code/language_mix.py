"""calculate candidate tokenizer-training quotas, not an empirical optimum.

Default source sizes are explicitly hypothetical. Count actual cleaned Unicode
characters before supplying --de-chars and --es-chars. This script never claims
to train a tokenizer or evaluate German/Spanish language quality.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]


def allocate(sizes: dict[str, int], alpha: float, budget: int) -> dict:
    if not 0 <= alpha <= 1:
        raise ValueError('alpha must be between 0 and 1')
    if budget < 0 or any(v < 0 for v in sizes.values()):
        raise ValueError('Character counts must be nonnegative')
    # A language with no available text must not acquire weight through 0**0.
    masses = {k: v**alpha if v else 0.0 for k, v in sizes.items()}
    total = sum(masses.values())
    if total == 0:
        raise ValueError('At least one language needs available text')
    probabilities = {k: v / total for k, v in masses.items()}
    exact = {k: budget * p for k, p in probabilities.items()}
    quotas = {k: math.floor(v) for k, v in exact.items()}
    remaining = budget - sum(quotas.values())
    order = sorted(quotas, key=lambda k: (-(exact[k] - quotas[k]), k))
    for k in order[:remaining]:
        quotas[k] += 1
    return {
        'alpha': alpha,
        'probabilities': probabilities,
        'character_quotas': quotas,
        'requires_reuse': {k: quotas[k] > sizes[k] for k in quotas},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--de-chars', type=int, default=9_000_000)
    parser.add_argument('--es-chars', type=int, default=1_000_000)
    parser.add_argument('--total-chars', type=int, default=1_000_000)
    args = parser.parse_args()
    sizes = {'de': args.de_chars, 'es': args.es_chars}
    plans = [allocate(sizes, a, args.total_chars) for a in (0.0, 0.5, 1.0)]
    checks = {
        'integer_quotas_sum_to_budget': all(sum(p['character_quotas'].values()) == args.total_chars for p in plans),
        'probabilities_sum_to_one': all(math.isclose(sum(p['probabilities'].values()), 1) for p in plans),
        'example_sqrt_9_to_1_gives_3_to_1': math.isclose(allocate({'de': 9, 'es': 1}, 0.5, 4)['probabilities']['de'], 0.75),
        'zero_source_does_not_get_a_quota': allocate({'de': 0, 'es': 10}, 0, 7)['character_quotas']['de'] == 0,
    }
    assert all(checks.values())
    result = {
        'scope': '候选配额计算。默认语料大小是明确假设，不是下载、测量或训练结果。',
        'source_characters_assumed': sizes,
        'training_character_budget': args.total_chars,
        'counting_rule': '清洗、去重并按统一Unicode规范化后，对Python字符串用len计Unicode码点；不是UTF-8字节数，也不一定等于用户感知字符数。',
        'plans': plans,
        'checks': checks,
        'limitations': [
            '这些配额不是最佳语言比例结论；需在独立验证集比较tokenizer。',
            '若配额超过可用语料，先减少预算或限制重复次数，不可把重复文本当作新增独立信息。',
            '真实采样应保持句子或文档完整，记录实际字符比例；不要按UTF-8原始字节截断。',
        ],
    }
    outdir = ROOT / 'results'
    outdir.mkdir(exist_ok=True)
    (outdir / 'language_mix.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [result['scope'], f'假设可用字符数：{sizes}；训练预算：{args.total_chars}']
    for p in plans:
        lines.append(f"alpha={p['alpha']}: 比例={p['probabilities']}, 字符配额={p['character_quotas']}")
    lines.append('4项配额与边界检查通过；未进行真实语料训练。')
    (outdir / 'language_mix.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
