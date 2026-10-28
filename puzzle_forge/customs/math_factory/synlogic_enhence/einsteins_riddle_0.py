# einsteins_riddle_1.py
import random

def choose_item(lst):
    """Return one random element from the given list."""
    if not isinstance(lst, list) or len(lst) == 0:
        raise ValueError("choose_item expects a non-empty list")
    return random.choice(lst)

def choose_pair_distinct(lst):
    """Return two distinct elements from the list as [a, b]."""
    if not isinstance(lst, list) or len(lst) < 2:
        raise ValueError("choose_pair_distinct expects a list with at least 2 items")
    a, b = random.sample(lst, 2)
    return [a, b]

def choose_sample_distinct(lst, k):
    """Return a list of k distinct elements sampled from lst."""
    if not isinstance(lst, list) or len(lst) < k:
        raise ValueError("choose_sample_distinct expects list length >= k")
    return random.sample(lst, k)

def shuffle_list(lst):
    """Return a shuffled shallow copy of the list."""
    if not isinstance(lst, list):
        raise ValueError("shuffle_list expects a list")
    tmp = lst[:]
    random.shuffle(tmp)
    return tmp