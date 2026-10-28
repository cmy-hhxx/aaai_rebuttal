# blood_donation_puzzle_2.py
# Custom operators used by the YAML specification.

from typing import List, Any, Tuple
from z3 import And, Or, Distinct

import random


def distinct_list(lst):
    """Return a Z3 Distinct constraint over the given list of Z3 Ints."""
    return Distinct(*lst)


def positions_in_range(lst, n):
    """Constrain each Z3 Int in lst to be in [1, n] (1-based positions)."""
    return And(*[And(x >= 1, x <= n) for x in lst])


def find_label_by_equal_pos(labels: List[Any], positions: List[int], target_pos: int) -> Any:
    """
    Given parallel lists labels and positions, return the label whose position equals target_pos.
    Assumes exactly one match.
    """
    for lab, pos in zip(labels, positions):
        if pos == target_pos:
            return lab
    return None  # Fallback: not expected in valid puzzles


def shuffle_list(lst: List[Any]) -> List[Any]:
    """Return a randomly shuffled copy of the input list."""
    out = list(lst)
    random.shuffle(out)
    return out


def sample_list(lst: List[Any], k: int) -> List[Any]:
    """Sample k distinct elements from lst, shuffle order."""
    if k > len(lst):
        raise ValueError('k cannot be larger than list length in sample_list')
    res = random.sample(lst, k)
    random.shuffle(res)
    return res


def sample_sorted(lst: List[int], k: int) -> List[int]:
    """Sample k distinct integers from lst and return them sorted ascending."""
    if k > len(lst):
        raise ValueError('k cannot be larger than list length in sample_sorted')
    res = random.sample(lst, k)
    res.sort()
    return res


# ------------------------------
# Generalized relation helpers
# ------------------------------

def get_pos_by_tag(
    tagged: Tuple[str, Any],
    pos_name, pos_btype, pos_weight, pos_age, pos_shirt, pos_job
):
    """
    Given a tagged tuple ('category', label), return the corresponding Z3 position symbol.
    Supported categories: 'name', 'btype', 'weight', 'age', 'shirt', 'job'.
    """
    tag, lab = tagged
    if tag == 'name':
        return pos_name[lab]
    if tag == 'btype':
        return pos_btype[lab]
    if tag == 'weight':
        return pos_weight[lab]
    if tag == 'age':
        return pos_age[lab]
    if tag == 'shirt':
        return pos_shirt[lab]
    if tag == 'job':
        return pos_job[lab]
    raise ValueError(f'Unknown tag: {tag}')


def adj_positions(x, y):
    """Adjacent relation: x next to y."""
    return Or(x + 1 == y, x == y + 1)


def left_of_positions(x, y):
    """Left-of relation: x somewhere to the left of y."""
    return x < y


def exact_left_of_positions(x, y):
    """Exact-left relation: x exactly to the left of y."""
    return x + 1 == y


def at_ends_positions(x, n: int):
    """At-ends relation: x is at position 1 or n (1-based)."""
    return Or(x == 1, x == n)


def between_positions(a, b, c):
    """Between relation: b is strictly between a and c in that order."""
    return And(a < b, b < c)


def label_text(tagged: Tuple[str, Any]) -> str:
    """
    Convert a tagged tuple into human-friendly text used in desc strings.
    - name: the person's name
    - btype: the <type> donor
    - weight: the person weighing <w> lb
    - age: the <a> year old
    - shirt: the person in the <color> shirt
    - job: the <job>
    """
    tag, lab = tagged
    if tag == 'name':
        return str(lab)
    if tag == 'btype':
        return f'the {lab} donor'
    if tag == 'weight':
        return f'the person weighing {lab} lb'
    if tag == 'age':
        return f'the {lab} year old'
    if tag == 'shirt':
        return f'the person in the {lab} shirt'
    if tag == 'job':
        return str(lab)
    raise ValueError(f'Unknown tag for text: {tag}')


# ------------------------------
# New complexity helpers
# ------------------------------

def gap_positions(x, y, k: int):
    """Exact gap relation: positions differ by k."""
    return Or(x - y == k, y - x == k)


def next_to_end_positions(x, n: int):
    """x is next to one of the ends: position 2 or n-1 when n >= 3 (1-based)."""
    if n < 3:
        # With fewer than 3 positions, being "next to an end" degenerates to being at ends
        return Or(x == 1, x == n)
    return Or(x == 2, x == n - 1)


def position_in_set(x, allowed: List[int]):
    """x is equal to one of the allowed positions."""
    return Or(*[x == p for p in allowed])


def order_three_positions(a, b, c):
    """Strict order a < b < c."""
    return And(a < b, b < c)


def older_than_pos(pos_age_dict, ages_list: List[int], x_pos, y_pos):
    """
    The person at x_pos is older than the person at y_pos.
    Build an Or over all pairs of age labels (ai, aj) with ages_list[i] > ages_list[j]:
    And(pos_age[ai] == x_pos, pos_age[aj] == y_pos)
    """
    clauses = []
    for i, ai in enumerate(ages_list):
        for j, aj in enumerate(ages_list):
            if ages_list[i] > ages_list[j]:
                clauses.append(And(pos_age_dict[ai] == x_pos, pos_age_dict[aj] == y_pos))
    if not clauses:
        return x_pos != y_pos
    return Or(*clauses)


def heavier_than_pos(pos_weight_dict, weights_list: List[int], x_pos, y_pos):
    """
    The person at x_pos is heavier than the person at y_pos.
    Build an Or over all pairs of weight labels (wi, wj) with weights_list[i] > weights_list[j]:
    And(pos_weight[wi] == x_pos, pos_weight[wj] == y_pos)
    """
    clauses = []
    for i, wi in enumerate(weights_list):
        for j, wj in enumerate(weights_list):
            if weights_list[i] > weights_list[j]:
                clauses.append(And(pos_weight_dict[wi] == x_pos, pos_weight_dict[wj] == y_pos))
    if not clauses:
        return x_pos != y_pos
    return Or(*clauses)