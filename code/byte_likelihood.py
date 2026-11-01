"""Exact UTF-8 string scores for a token bigram with a sentence-end symbol."""
from collections import defaultdict
from functools import cache
from math import inf, log2


def log2_sum(values):
    """Add probabilities supplied as base-two logs, without underflow."""
    if not values:
        return -inf
    if len(values) == 1:
        return values[0]
    largest = max(values)
    if largest == -inf:
        return -inf
    return largest + log2(sum(2.0 ** (value - largest) for value in values))


class ByteBigramLikelihood:
    """Sum the probability of every token path that emits the observed bytes."""

    def __init__(self, vocab, bos, eos, log2_transition):
        if bos == eos or bos in vocab or eos in vocab:
            raise ValueError("BOS and EOS must be distinct from each other and from text tokens")
        self.bos, self.eos = bos, eos
        self.logp = cache(log2_transition)
        self.by_first_byte = defaultdict(list)
        for token_id, piece in vocab.items():
            if not piece:
                raise ValueError("Text tokens must emit at least one byte")
            self.by_first_byte[piece[0]].append((token_id, piece))

    def bits(self, raw: bytes) -> float:
        """Return -log2 P(raw, EOS | BOS). Impossible strings cost infinity."""
        # Each entry holds (previous token, log probability of reaching this
        # byte boundary with that token). That is all the history a bigram uses.
        ends_at = [[] for _ in range(len(raw) + 1)]
        ends_at[0].append((self.bos, 0.0))
        for offset, first_byte in enumerate(raw):
            incoming = ends_at[offset]
            if not incoming:
                continue
            for token_id, piece in self.by_first_byte[first_byte]:
                if raw.startswith(piece, offset):
                    score = log2_sum([weight + self.logp(previous, token_id)
                                      for previous, weight in incoming])
                    ends_at[offset + len(piece)].append((token_id, score))
        return -log2_sum([weight + self.logp(previous, self.eos)
                          for previous, weight in ends_at[-1]])
