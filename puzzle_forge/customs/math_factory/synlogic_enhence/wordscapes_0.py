# wordscapes_1.py  (unchanged)

import random
import string
from itertools import permutations
from typing import List, Dict, Tuple

def _random_word(length: int) -> str:
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

def rand_words(num: int, min_len: int, max_len: int, seed=None) -> List[str]:
    if seed is not None:
        random.seed(seed)
    words, heads = [], set()
    while len(words) < num:
        w = _random_word(random.randint(min_len, max_len))
        if w[0] in heads:
            continue
        heads.add(w[0])
        words.append(w)
    return words

def _to_ord(words: List[str]) -> List[List[int]]:
    return [[ord(ch) for ch in w] for w in words]

def _unique_solver(rows: List[str], cols: List[str]) -> Tuple[bool, List[int], List[int]]:
    n = len(rows)
    if len(cols) != n:
        return False, [], []
    rows_mat, cols_mat = _to_ord(rows), _to_ord(cols)
    sol_cnt, sol_rp, sol_cp = 0, None, None
    for cp in permutations(range(n)):
        if any(rows_mat[i][cp[i]] != cols_mat[cp[i]][i] for i in range(n)):
            continue
        for rp in permutations(range(n)):
            if all(rows_mat[rp[r]][c] == cols_mat[cp[c]][r] for r in range(n) for c in range(n)):
                sol_cnt += 1
                if sol_cnt == 1:
                    sol_rp, sol_cp = list(rp), list(cp)
                else:
                    return False, [], []
        if sol_cnt > 1:
            return False, [], []
    return sol_cnt == 1, sol_rp or [], sol_cp or []

def gen_cross_data(n: int, max_attempts: int = 400) -> Dict:
    for _ in range(max_attempts):
        eng = rand_words(n, n, n)
        grid = [list(w) for w in eng]
        fra = [''.join(grid[r][c] for r in range(n)) for c in range(n)]
        if len(set(fra)) != n or len({w[0] for w in fra}) != n:
            continue
        unique, rp, cp = _unique_solver(eng, fra)
        if unique:
            return {'eng': eng, 'fra': fra, 'row_perm': rp, 'col_perm': cp, 'grid': grid}
    raise ValueError('Unable to generate unique crossword')