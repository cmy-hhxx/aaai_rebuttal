# zebra_puzzle_5.py
import random
from typing import List, Any, Sequence

def shuffle_list(lst: List[Any]) -> List[Any]:
    """Return a shuffled copy of the input list."""
    tmp = list(lst)
    random.shuffle(tmp)
    return tmp

def pick_k_distinct(lst: Sequence[Any], k: int) -> List[Any]:
    """Pick k distinct items from lst."""
    if k > len(lst):
        raise ValueError("k cannot be larger than the list length")
    return random.sample(list(lst), k)

def pick_two_distinct(lst: Sequence[Any]):
    """Pick two distinct items from lst, return as a tuple."""
    a, b = random.sample(list(lst), 2)
    return (a, b)

def pick_one(lst: Sequence[Any]):
    """Pick one item from lst."""
    return random.choice(list(lst))

def pick_one_excluding(lst: Sequence[Any], exclude: Sequence[Any]):
    """Pick one item from lst excluding items in exclude."""
    pool = [x for x in lst if x not in exclude]
    if not pool:
        raise ValueError("No available items after exclusion")
    return random.choice(pool)