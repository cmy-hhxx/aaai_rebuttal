# einsteins_riddle_9.py
import random
from z3 import is_true

def pick_k(lst, k):
    """Return k unique random elements from lst (shuffled if k >= len(lst))."""
    if k <= 0:
        return []
    if k >= len(lst):
        out = lst[:]
        random.shuffle(out)
        return out[:k]
    return random.sample(lst, k)

def pick_one_exclude(lst, exclude):
    """Pick one element from lst excluding 'exclude'. If no candidate, return exclude."""
    candidates = [x for x in lst if x != exclude]
    if not candidates:
        return exclude
    return random.choice(candidates)

def get_position_of_surname(model, positions, surname_s, target):
    """
    Return 1-based position index of the target surname in the given Z3 model.
    - model: Z3 model
    - positions: list of position strings like ['1','2','3','4','5']
    - surname_s: dict-like mapping (pos_str, surname_str) -> BoolRef
    - target: surname string to locate
    """
    for idx, pos in enumerate(positions):
        key = (pos, target)
        if key not in surname_s:
            continue
        val = model.evaluate(surname_s[key], model_completion=True)
        if is_true(val):
            return idx + 1
    return -1

def unique_answer_for_surname(solutions, positions, surname_s, target):
    """
    Check whether the target surname has a unique position across all solutions.
    Return True when all solutions agree on the same position, otherwise False.
    If there is no solution, return False.
    """
    ans_set = set()
    for m in solutions:
        pos = get_position_of_surname(m, positions, surname_s, target)
        ans_set.add(pos)
        if len(ans_set) > 1:
            return False
    # If there is at least one solution and all give the same pos (>0), it's unique
    return len(ans_set) == 1 and next(iter(ans_set)) > 0

def get_unique_position_of_surname(solutions, positions, surname_s, target):
    """
    Return the unique position if all solutions agree; otherwise return -1.
    """
    if not solutions:
        return -1
    first_pos = get_position_of_surname(solutions[0], positions, surname_s, target)
    if first_pos <= 0:
        return -1
    for m in solutions[1:]:
        pos = get_position_of_surname(m, positions, surname_s, target)
        if pos != first_pos or pos <= 0:
            return -1
    return first_pos