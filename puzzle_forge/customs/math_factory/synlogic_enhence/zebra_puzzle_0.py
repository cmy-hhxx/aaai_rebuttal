# zebra_puzzle_0.py
# Helper module for generalized Zebra-style puzzle.
# Provides custom operators referenced by YAML.

import random
from typing import List

def gen_prefixed_labels(prefix: str, n: int) -> List[str]:
    """
    Generate labels with a given prefix and 1..n indices, e.g., N1..Nn.
    """
    return [f"{prefix}{i}" for i in range(1, n + 1)]

def pick_one(seq: List[str]) -> str:
    """
    Pick one element from a list uniformly at random.
    """
    if not seq:
        raise ValueError("Empty sequence in pick_one")
    return random.choice(seq)

def pick_two_distinct(seq: List[str]) -> List[str]:
    """
    Pick two distinct elements from a list uniformly at random.
    Returns a list of two items [a, b] with a != b.
    """
    if len(seq) < 2:
        raise ValueError("Sequence too short for pick_two_distinct")
    return random.sample(seq, 2)

def shuffle_labels(seq: List[str]) -> List[str]:
    """
    Return a new list which is a random permutation of the input sequence.
    """
    res = list(seq)
    random.shuffle(res)
    return res