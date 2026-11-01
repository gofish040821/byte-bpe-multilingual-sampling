"""Check the forward sum against exhaustive token paths on short strings."""
import math
import sys
import unittest
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from byte_likelihood import ByteBigramLikelihood


class ByteLikelihoodTest(unittest.TestCase):
    def test_matches_enumeration_including_eos(self):
        # Two tokens spell "ab"; both paths matter, as does the path via a,b.
        vocab = {0: b"a", 1: b"b", 2: b"ab", 3: b"ab"}
        bos, eos = 4, 5

        def probability(prev, nxt):
            outcomes = [*vocab, eos]
            weights = [1 + (prev + 2 * token) % 7 for token in outcomes]
            return weights[outcomes.index(nxt)] / sum(weights)

        scorer = ByteBigramLikelihood(vocab, bos, eos, lambda p, n: math.log2(probability(p, n)))
        for raw in [b"", b"a", b"ab", b"abab", b"bbba", b"x"]:
            total = 0.0
            for size in range(len(raw) + 1):
                for tokens in product(vocab, repeat=size):
                    if b"".join(vocab[token] for token in tokens) == raw:
                        total += math.prod(probability(a, b)
                                           for a, b in zip((bos, *tokens), (*tokens, eos)))
            expected = -math.log2(total) if total else math.inf
            self.assertAlmostEqual(scorer.bits(raw), expected, places=12)

    def test_long_string_does_not_underflow(self):
        scorer = ByteBigramLikelihood({0: b"x"}, 1, 2, lambda p, n: -1.0)
        self.assertEqual(scorer.bits(b"x" * 4096), 4097.0)
