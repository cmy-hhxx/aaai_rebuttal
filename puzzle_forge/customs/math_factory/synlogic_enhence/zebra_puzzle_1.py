# zebra_puzzle_13.py
import random

def shuffle_list(lst):
    """
    Return a new list that is a random permutation of the input list.
    Ensures variability across runs for robust puzzle generation.
    """
    cp = list(lst)
    random.shuffle(cp)
    return cp

# Optional utilities (not referenced by YAML directly, kept for future extension)
def biased_shuffle(lst, bias_first=False):
    """Optionally bias the first element to increase variety in anchors."""
    cp = list(lst)
    random.shuffle(cp)
    if bias_first and len(cp) > 2:
        i = random.randrange(len(cp) - 1)
        cp[i], cp[-1] = cp[-1], cp[i]
    return cp

def choose_unique_pairs(items, k):
    """Return k unique pairs (unordered) from items."""
    items = list(items)
    random.shuffle(items)
    res = []
    seen = set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            pair = tuple(sorted((items[i], items[j])))
            if pair not in seen:
                seen.add(pair)
                res.append(pair)
                if len(res) >= k:
                    return res
    return res