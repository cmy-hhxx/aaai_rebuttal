# ================================================================
# word_sorting_0.py — export functions explicitly & uniqueness fix
# ================================================================
import random, string
from typing import List, Dict, Callable, Sequence, Any, Tuple
from z3 import Solver, Int, Distinct, And, Or, sat, unsat

__all__ = [
    "random_choice",
    "pick_random_letters",
    "build_custom_alphabet",
    "gen_random_words",
    "custom_sort_words",
    "generate_order_clues",
    "op_gen_rules",
]

# ---------------- Random helpers ----------------
def random_choice(seq: Sequence[Any]) -> Any:
    return random.choice(list(seq))

def pick_random_letters(n: int) -> List[str]:
    return random.sample(string.ascii_lowercase, k=n)

def build_custom_alphabet(moved: List[str], position: str = 'front') -> List[str]:
    remain = [c for c in string.ascii_lowercase if c not in moved]
    return moved + remain if position == 'front' else remain + moved

def gen_random_words(num: int, min_len: int = 4, max_len: int = 9) -> List[str]:
    words = set()
    while len(words) < num:
        words.add(''.join(random.choices(string.ascii_lowercase, k=random.randint(min_len, max_len))))
    return list(words)

def custom_sort_words(words: List[str], alphabet: List[str], descending: bool) -> List[str]:
    order = {ch: idx for idx, ch in enumerate(alphabet)}
    return sorted(words, key=lambda w: [order.get(c, -1) for c in w.lower()], reverse=descending)

# ------------- Uniqueness verifier ----------------
def _is_unique(words: List[str], pairs: List[Tuple[str, str]]) -> bool:
    s = Solver()
    n = len(words)
    pos = {w: Int(w) for w in words}
    s.add([And(pos[w] >= 0, pos[w] < n) for w in words])
    s.add(Distinct(*pos.values()))
    for a, b in pairs:
        s.add(pos[a] < pos[b])
    if s.check() != sat:
        return False
    model = s.model()
    s.add(Or(*[pos[w] != model[pos[w]] for w in words]))
    return s.check() == unsat  # unsat ⇒ unique

# ------------- Clue generator ---------------------
def generate_order_clues(sorted_words: List[str],
                         min_clue: int,
                         max_clue: int) -> Dict[str, Any]:
    n = len(sorted_words)
    idx = {w: i for i, w in enumerate(sorted_words)}
    all_pairs = [(sorted_words[i], sorted_words[j])
                 for i in range(n) for j in range(i + 1, n)]
    non_adj = [(a, b) for a, b in all_pairs if abs(idx[a] - idx[b]) >= 2]

    for _ in range(40):
        clues = [random.choice(non_adj)]
        remaining = [p for p in all_pairs if p not in clues]
        random.shuffle(remaining)
        for a, b in remaining:
            if len(clues) >= max_clue:
                break
            clues.append((a, b))
            if len(clues) >= min_clue and _is_unique(sorted_words, clues):
                break
        if len(clues) >= min_clue and _is_unique(sorted_words, clues):
            break
    else:
        clues = [(sorted_words[i], sorted_words[i + 1]) for i in range(min(n - 1, max_clue))]

    desc = "\\n".join(f'· {a} 位于 {b} 之前' for a, b in clues)
    return {"pairs": clues, "desc": desc}

# ------------- Operator registry ------------------
def op_gen_rules() -> Dict[str, Callable]:
    return {
        "random_choice":         random_choice,
        "pick_random_letters":   pick_random_letters,
        "build_custom_alphabet": build_custom_alphabet,
        "gen_random_words":      gen_random_words,
        "custom_sort_words":     custom_sort_words,
        "generate_order_clues":  generate_order_clues
    }