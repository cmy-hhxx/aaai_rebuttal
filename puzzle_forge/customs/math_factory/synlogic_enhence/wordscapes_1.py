# wordscapes_0.py
import json
import random
from typing import List, Tuple, Dict, Any, Optional, Set

# ---------------------------
# Utility helpers
# ---------------------------

def count_X(grid: List[List[str]]) -> int:
    return sum(1 for row in grid for c in row if c == 'X')


def gen_alphabet(k: int) -> List[str]:
    """
    Generate a random alphabet of size k with distinct lowercase letters.
    """
    base = list('abcdefghijklmnopqrstuvwxyz')
    random.shuffle(base)
    k = max(1, min(k, len(base)))
    return base[:k]


def to_json(grid: List[List[str]]) -> str:
    return json.dumps(grid)


def dict_get(d: Dict[str, Any], key: str) -> Any:
    return d.get(key, None)


def format_grid_plain(grid: List[List[str]]) -> str:
    """
    Render a grid (list of list of single-character strings) into a
    quote-free nested list string, e.g., [[a, b], [ , c]]
    """
    rows_str = []
    for row in grid:
        cells = ', '.join(ch if ch != '' else ' ' for ch in row)
        rows_str.append('[' + cells + ']')
    return '[' + ', '.join(rows_str) + ']'


# ---------------------------
# Grid analysis
# ---------------------------

def _find_across_runs(grid: List[List[str]]) -> List[Tuple[int, int, int]]:
    """
    Find horizontal runs of X.
    Returns: [(row, start_col, end_col)], inclusive.
    """
    runs = []
    R, C = len(grid), len(grid[0]) if grid else 0
    for r in range(R):
        c = 0
        while c < C:
            if grid[r][c] == 'X':
                start = c
                while c + 1 < C and grid[r][c + 1] == 'X':
                    c += 1
                end = c
                runs.append((r, start, end))
            c += 1
    return runs


def _find_down_runs(grid: List[List[str]]) -> List[Tuple[int, int, int]]:
    """
    Find vertical runs of X.
    Returns: [(start_row, end_row, col)], inclusive.
    """
    runs = []
    R, C = len(grid), len(grid[0]) if grid else 0
    for c in range(C):
        r = 0
        while r < R:
            if grid[r][c] == 'X':
                start = r
                while r + 1 < R and grid[r + 1][c] == 'X':
                    r += 1
                end = r
                runs.append((start, end, c))
            r += 1
    return runs


def _random_row(cols: int, min_run: int, max_run: int) -> List[str]:
    """
    Generate a random row of 'X' and '0' of length cols. 'X' segments have length in [min_run, max_run],
    '0' segments have length in [1, 2]. Alternates segment types.
    """
    segs: List[str] = []
    length_acc = 0
    current = random.choice(['0', 'X'])
    while length_acc < cols:
        if current == 'X':
            run_len = random.randint(min_run, max_run)
        else:
            run_len = random.randint(1, 2)
        if length_acc + run_len > cols:
            run_len = cols - length_acc
        segs.extend([current] * run_len)
        length_acc += run_len
        current = 'X' if current == '0' else '0'
    return segs


def _valid_runs(grid: List[List[str]],
                across_min: int, across_max: int,
                down_min: int, down_max: int) -> bool:
    """
    Check across runs lengths in [across_min, across_max] and down runs in [down_min, down_max].
    Ensure at least 2 runs in each direction.
    """
    across = _find_across_runs(grid)
    down = _find_down_runs(grid)
    if len(across) < 2 or len(down) < 2:
        return False
    for (_, s, e) in across:
        L = e - s + 1
        if L < across_min or L > across_max:
            return False
    for (sr, er, _) in down:
        L = er - sr + 1
        if L < down_min or L > down_max:
            return False
    return True


def _generate_grid(rows: int, cols: int,
                   across_min: int, across_max: int,
                   down_min: int, down_max: int,
                   max_attempts: int = 2000) -> List[List[str]]:
    """
    Generate grid of 'X' and '0' with valid across/down run lengths.
    """
    for _ in range(max_attempts):
        grid = [_random_row(cols, across_min, across_max) for _ in range(rows)]
        if _valid_runs(grid, across_min, across_max, down_min, down_max):
            return grid
    # If not found, keep trying with a different strategy: bias to shorter X runs
    for _ in range(max_attempts):
        grid = []
        for _r in range(rows):
            row = []
            while len(row) < cols:
                # prefer alternating segments with X lengths centered near min, zeros short
                if random.random() < 0.5:
                    run_x = random.randint(across_min, min(across_min + 1, across_max))
                    row.extend(['X'] * min(run_x, cols - len(row)))
                else:
                    run_0 = random.randint(1, 2)
                    row.extend(['0'] * min(run_0, cols - len(row)))
            grid.append(row)
        if _valid_runs(grid, across_min, across_max, down_min, down_max):
            return grid
    # As a last resort, raise error to avoid producing inconsistent puzzles
    raise RuntimeError("Failed to generate a grid satisfying run-length constraints")


# ---------------------------
# Word utilities
# ---------------------------

def _extract_down_words_from_filled(filled: List[List[str]], grid: List[List[str]]) -> List[str]:
    down_words: List[str] = []
    for (sr, er, c) in _find_down_runs(grid):
        word = ''.join(filled[r][c] for r in range(sr, er + 1))
        down_words.append(word)
    return down_words


def _extract_across_words_from_filled(filled: List[List[str]], grid: List[List[str]]) -> List[str]:
    across_words: List[str] = []
    for (r, s, e) in _find_across_runs(grid):
        word = ''.join(filled[r][c] for c in range(s, e + 1))
        across_words.append(word)
    return across_words


def _has_duplicates(lst: List[str]) -> bool:
    return len(set(lst)) != len(lst)


def _grid_spaces_template(grid: List[List[str]]) -> List[List[Optional[str]]]:
    """
    Template with spaces in '0' cells and None in 'X' cells.
    """
    R, C = len(grid), len(grid[0]) if grid else 0
    return [[' ' if grid[r][c] == '0' else None for c in range(C)] for r in range(R)]


def _place_across_words_into_template(grid: List[List[str]], across_words: List[str]) -> List[List[str]]:
    out = _grid_spaces_template(grid)
    runs = _find_across_runs(grid)
    for idx, (r, s, e) in enumerate(runs):
        w = across_words[idx]
        assert (e - s + 1) == len(w)
        for k, ch in enumerate(w):
            out[r][s + k] = ch
    # type: ignore
    return out  # fully filled letters and spaces


# ---------------------------
# Rule checks
# ---------------------------

_VOWELS = set('aeiou')

def _is_vowel(ch: str) -> bool:
    return ch in _VOWELS

def _is_consonant(ch: str) -> bool:
    return ch.isalpha() and ch not in _VOWELS

def _check_intersection_rule(grid: List[List[str]], out: List[List[str]], rule_code: int) -> bool:
    """
    rule_code: 0 none, 1 vowels only, 2 consonants only at intersections.
    Intersection positions are cells that belong to both an across and a down run.
    """
    if rule_code == 0:
        return True
    R, C = len(grid), len(grid[0]) if grid else 0
    # Mark across cells
    across_mask = [[False]*C for _ in range(R)]
    for (r, s, e) in _find_across_runs(grid):
        for c in range(s, e+1):
            across_mask[r][c] = True
    # Mark down cells
    down_mask = [[False]*C for _ in range(R)]
    for (sr, er, c) in _find_down_runs(grid):
        for r in range(sr, er+1):
            down_mask[r][c] = True
    # Check intersections
    for r in range(R):
        for c in range(C):
            if across_mask[r][c] and down_mask[r][c]:
                ch = out[r][c]
                if ch == ' ' or ch is None:
                    return False
                if rule_code == 1 and not _is_vowel(ch):
                    return False
                if rule_code == 2 and not _is_consonant(ch):
                    return False
    return True


def _check_no_adjacent_identical(out: List[List[str]]) -> bool:
    """
    No equal letters adjacent horizontally or vertically.
    Spaces are ignored. None should not appear in a completed grid.
    """
    R, C = len(out), len(out[0]) if out else 0
    for r in range(R):
        for c in range(C):
            ch = out[r][c]
            if ch == ' ':
                continue
            if r+1 < R and out[r+1][c] == ch:
                return False
            if c+1 < C and out[r][c+1] == ch:
                return False
    return True


def _letter_count(out: List[List[str]], letter: str) -> int:
    return sum(1 for row in out for ch in row if ch == letter)


def _check_row_vowel_even(out: List[List[str]], grid: List[List[str]]) -> bool:
    """
    For each row, count vowels in X cells; the count must be even.
    """
    R, C = len(out), len(out[0]) if out else 0
    for r in range(R):
        cnt = 0
        for c in range(C):
            if grid[r][c] == 'X':
                ch = out[r][c]
                if ch != ' ' and _is_vowel(ch):
                    cnt += 1
        if cnt % 2 != 0:
            return False
    return True


def _check_col_consonant_odd(out: List[List[str]], grid: List[List[str]]) -> bool:
    """
    For each column that has at least one X cell, the consonant count in X cells must be odd.
    """
    R, C = len(out), len(out[0]) if out else 0
    for c in range(C):
        has_x = any(grid[r][c] == 'X' for r in range(R))
        if not has_x:
            continue
        cnt = 0
        for r in range(R):
            if grid[r][c] == 'X':
                ch = out[r][c]
                if ch != ' ' and _is_consonant(ch):
                    cnt += 1
        if cnt % 2 != 1:
            return False
    return True


def _check_diag_distinct(out: List[List[str]], grid: List[List[str]]) -> bool:
    """
    Letters on the main diagonal positions where grid has X must be all distinct.
    """
    R, C = len(out), len(out[0]) if out else 0
    diag_letters: List[str] = []
    for r in range(min(R, C)):
        if grid[r][r] == 'X':
            ch = out[r][r]
            if ch == ' ':
                return False
            diag_letters.append(ch)
    return len(set(diag_letters)) == len(diag_letters)


def _is_palindrome(w: str) -> bool:
    return w == w[::-1]


# ---------------------------
# Uniqueness checkers
# ---------------------------

def verify_unique_fill(grid: List[List[str]],
                       across_words: List[str],
                       down_words: List[str],
                       filled_grid: List[List[str]],
                       intersection_rule: int,
                       forbid_adjacent: bool,
                       quota_letter: Optional[str],
                       quota_count: Optional[int],
                       row_vowel_even: bool,
                       col_cons_odd: bool,
                       prefix_set: Optional[List[str]],
                       suffix_set: Optional[List[str]],
                       diag_distinct: bool,
                       no_pal_across: bool) -> bool:
    """
    Legacy deterministic uniqueness check with fixed across order.
    Preserved for backward compatibility but not used in the new YAML.
    """
    # Basic duplicate avoidance for symmetry
    if _has_duplicates(across_words) or _has_duplicates(down_words):
        return False

    across_runs = _find_across_runs(grid)
    if len(across_runs) != len(across_words):
        return False
    # Check length match
    for idx, (r, s, e) in enumerate(across_runs):
        if (e - s + 1) != len(across_words[idx]):
            return False

    # Enforce prefix/no-pal/adjacent within-run constraints on across words
    if prefix_set is not None:
        for w in across_words:
            if len(w) == 0 or w[0] not in prefix_set:
                return False
    if no_pal_across and any(_is_palindrome(w) for w in across_words):
        return False
    if forbid_adjacent and any(any(w[k] == w[k+1] for k in range(len(w) - 1)) for w in across_words):
        return False

    # Build the only allowed filled grid (deterministic placement)
    out = _place_across_words_into_template(grid, across_words)

    # Down words multiset check
    down_runs = _find_down_runs(grid)
    actual_down: List[str] = []
    for (sr, er, c) in down_runs:
        word = ''.join(out[r][c] for r in range(sr, er + 1))
        actual_down.append(word)
    # multiset compare
    def multiset(lst: List[str]) -> Dict[str, int]:
        d: Dict[str, int] = {}
        for w in lst:
            d[w] = d.get(w, 0) + 1
        return d
    if multiset(actual_down) != multiset(down_words):
        return False

    # Intersection rule
    if not _check_intersection_rule(grid, out, intersection_rule):
        return False
    # Adjacent rule
    if forbid_adjacent and not _check_no_adjacent_identical(out):
        return False
    # Quota rule
    if quota_letter is not None and quota_count is not None:
        if _letter_count(out, quota_letter) != quota_count:
            return False
    # Row vowel even
    if row_vowel_even and not _check_row_vowel_even(out, grid):
        return False
    # Col consonant odd
    if col_cons_odd and not _check_col_consonant_odd(out, grid):
        return False
    # Diagonal distinct
    if diag_distinct and not _check_diag_distinct(out, grid):
        return False
    # Across prefix set already checked; Down suffix set:
    if suffix_set is not None:
        for w in actual_down:
            if len(w) == 0 or w[-1] not in suffix_set:
                return False

    return out == filled_grid


def verify_unique_fill_sets(grid: List[List[str]],
                            across_words: List[str],
                            down_words: List[str],
                            filled_grid: List[List[str]],
                            intersection_rule: int,
                            forbid_adjacent: bool,
                            quota_letter: Optional[str],
                            quota_count: Optional[int],
                            row_vowel_even: bool,
                            col_cons_odd: bool,
                            prefix_set: Optional[List[str]],
                            suffix_set: Optional[List[str]],
                            diag_distinct: bool,
                            no_pal_across: bool,
                            across_min: int,
                            across_max: int,
                            down_min: int,
                            down_max: int) -> bool:
    """
    Uniqueness checker under "unordered across words set" + "unordered down words set".
    Checks:
      - Grid's across/down X-run lengths in required ranges.
      - All given rules (intersection, adjacency, parity, diag distinct, no palindrome, prefix/suffix, quota).
      - Down words multiset must match exactly.
      - Uniqueness is judged by the number of distinct final grids (not assignments).
      - The unique grid must equal 'filled_grid'.
    """
    # 1) Run-length constraints
    if not _valid_runs(grid, across_min, across_max, down_min, down_max):
        return False

    # 2) Precompute structures
    across_runs = _find_across_runs(grid)
    down_runs = _find_down_runs(grid)
    R, C = len(grid), len(grid[0]) if grid else 0

    # 3) Length feasibility quick check
    from collections import Counter
    need_len = Counter([(e - s + 1) for (_, s, e) in across_runs])
    have_len = Counter([len(w) for w in across_words])
    if need_len != have_len:
        return False

    # 4) Prepare counts and masks
    out: List[List[Optional[str]]] = _grid_spaces_template(grid)
    row_vcnt = [0] * R
    col_ccnt = [0] * C
    diag_used: Set[str] = set()

    # Positions helpful for constraints
    last_x_in_row: List[Optional[int]] = [None] * R
    for r in range(R):
        for c in range(C-1, -1, -1):
            if grid[r][c] == 'X':
                last_x_in_row[r] = c
                break
    last_x_in_col: List[Optional[int]] = [None] * C
    for c in range(C):
        for r in range(R-1, -1, -1):
            if grid[r][c] == 'X':
                last_x_in_col[c] = r
                break
    # intersection mask
    across_mask = [[False]*C for _ in range(R)]
    for (r, s, e) in across_runs:
        for c in range(s, e+1):
            across_mask[r][c] = True
    down_mask = [[False]*C for _ in range(R)]
    for (sr, er, c) in down_runs:
        for r in range(sr, er+1):
            down_mask[r][c] = True
    intersection_mask = [[across_mask[r][c] and down_mask[r][c] for c in range(C)] for r in range(R)]
    down_end: Set[Tuple[int, int]] = set((er, c) for (sr, er, c) in down_runs)

    # 5) Multiset for across and down
    aw_count: Dict[str, int] = {}
    for w in across_words:
        aw_count[w] = aw_count.get(w, 0) + 1
    dw_count_target: Dict[str, int] = {}
    for w in down_words:
        dw_count_target[w] = dw_count_target.get(w, 0) + 1

    def allowed_letter_check(r: int, c: int, ch: str, left_ch: Optional[str]) -> bool:
        # prefix handled at word level for first character
        # intersection rule
        if intersection_rule != 0 and intersection_mask[r][c]:
            if intersection_rule == 1 and not _is_vowel(ch):
                return False
            if intersection_rule == 2 and not _is_consonant(ch):
                return False
        # down suffix set: only check when this cell is at the end of a down run
        if suffix_set is not None and (r, c) in down_end:
            if ch not in suffix_set:
                return False
        # forbid adjacency identical
        if forbid_adjacent:
            # left
            if left_ch is not None and left_ch == ch:
                return False
            # up
            if r - 1 >= 0 and grid[r][c] == 'X' and grid[r-1][c] == 'X':
                up_ch = out[r-1][c]
                if up_ch is not None and up_ch != ' ' and up_ch == ch:
                    return False
        # diag distinct
        if diag_distinct and r == c and grid[r][c] == 'X':
            if ch in diag_used:
                return False
        return True

    solutions: Set[str] = set()
    max_solutions = 2  # early exit if more than 1 distinct grid

    # Backtracking over across runs (row-major)
    def assign_run(idx: int) -> None:
        nonlocal solutions
        if len(solutions) >= max_solutions:
            return
        if idx == len(across_runs):
            # all across assigned: build final down words
            filled: List[List[str]] = [[' ' if out[r][c] in (None, ' ') else str(out[r][c]) for c in range(C)] for r in range(R)]
            # Check all global rules
            if not _check_intersection_rule(grid, filled, intersection_rule):
                return
            if forbid_adjacent and not _check_no_adjacent_identical(filled):
                return
            if row_vowel_even and not _check_row_vowel_even(filled, grid):
                return
            if col_cons_odd and not _check_col_consonant_odd(filled, grid):
                return
            if diag_distinct and not _check_diag_distinct(filled, grid):
                return
            if quota_letter is not None and quota_count is not None:
                if _letter_count(filled, quota_letter) != quota_count:
                    return
            # Down words multiset
            actual_down = _extract_down_words_from_filled(filled, grid)
            dcnt: Dict[str, int] = {}
            for w in actual_down:
                dcnt[w] = dcnt.get(w, 0) + 1
            if dcnt != dw_count_target:
                return
            # Unique by final grid
            sol_key = json.dumps(filled)
            solutions.add(sol_key)
            return

        r, s, e = across_runs[idx]
        L = e - s + 1
        # gather candidate words of length L with remaining count
        # small heuristic: shuffle to avoid bias
        candidates = [w for w, cnt in aw_count.items() if cnt > 0 and len(w) == L]
        random.shuffle(candidates)
        for w in candidates:
            # word-level checks
            if prefix_set is not None and (len(w) == 0 or w[0] not in prefix_set):
                continue
            if no_pal_across and _is_palindrome(w):
                continue
            if forbid_adjacent and any(w[i] == w[i+1] for i in range(len(w)-1)):
                continue
            # place character by character with incremental checks
            placed_positions: List[Tuple[int, int, Optional[str], bool]] = []  # (r,c,left_ch,diag_used_added)
            ok = True
            for pos in range(L):
                c = s + pos
                ch = w[pos]
                left_ch = w[pos-1] if pos > 0 else None
                if not allowed_letter_check(r, c, ch, left_ch):
                    ok = False
                    break
                # Update parity previews (for last in row/col enforce parity)
                # place tentatively
                out[r][c] = ch
                added_diag = False
                if diag_distinct and r == c and grid[r][c] == 'X':
                    diag_used.add(ch)
                    added_diag = True
                if _is_vowel(ch):
                    row_vcnt[r] += 1
                if _is_consonant(ch):
                    col_ccnt[c] += 1
                placed_positions.append((r, c, left_ch, added_diag))
                # If last X in row, enforce even vowels
                if last_x_in_row[r] == c and row_vowel_even:
                    if row_vcnt[r] % 2 != 0:
                        ok = False
                        break
                # If last X in col, enforce odd consonants
                if last_x_in_col[c] == r and col_cons_odd:
                    if col_ccnt[c] % 2 != 1:
                        ok = False
                        break
            if not ok:
                # rollback
                for (pr, pc, _l, added_diag) in reversed(placed_positions):
                    if added_diag and diag_distinct:
                        try:
                            diag_used.remove(out[pr][pc])  # type: ignore
                        except KeyError:
                            pass
                    ch2 = out[pr][pc]
                    if ch2 is not None and ch2 != ' ':
                        if _is_vowel(ch2):
                            row_vcnt[pr] -= 1
                        if _is_consonant(ch2):
                            col_ccnt[pc] -= 1
                    out[pr][pc] = None
                continue

            # commit this word
            aw_count[w] -= 1
            assign_run(idx + 1)
            # rollback
            aw_count[w] += 1
            for (pr, pc, _l, added_diag) in reversed(placed_positions):
                if added_diag and diag_distinct:
                    try:
                        diag_used.remove(out[pr][pc])  # type: ignore
                    except KeyError:
                        pass
                ch2 = out[pr][pc]
                if ch2 is not None and ch2 != ' ':
                    if _is_vowel(ch2):
                        row_vcnt[pr] -= 1
                    if _is_consonant(ch2):
                        col_ccnt[pc] -= 1
                out[pr][pc] = None
            if len(solutions) >= max_solutions:
                return

    assign_run(0)

    # Unique and matches provided filled_grid
    if len(solutions) != 1:
        return False
    target_key = json.dumps([row[:] for row in filled_grid])
    return target_key in solutions


# ---------------------------
# Generation helpers
# ---------------------------

def _prepare_alphabet(alphabet: List[str],
                      intersection_rule: int,
                      row_vowel_even: bool,
                      col_cons_odd: bool) -> List[str]:
    """
    Ensure feasibility: if rules require vowels/cons, inject one when missing.
    """
    s = set(alphabet)
    has_vowel = any(ch in _VOWELS for ch in s)
    has_cons = any(_is_consonant(ch) for ch in s)
    if intersection_rule == 1 and not has_vowel:
        alphabet = alphabet[:] + ['a']
        has_vowel = True
    if intersection_rule == 2 and not has_cons:
        alphabet = alphabet[:] + ['b']
        has_cons = True
    # For parity constraints, we need both types
    if (row_vowel_even or col_cons_odd) and not has_vowel:
        alphabet = alphabet[:] + ['a']
        has_vowel = True
    if (row_vowel_even or col_cons_odd) and not has_cons:
        alphabet = alphabet[:] + ['b']
    return alphabet


def _compute_constraint_maps(grid: List[List[str]]):
    R, C = len(grid), len(grid[0]) if grid else 0
    across_runs = _find_across_runs(grid)
    down_runs = _find_down_runs(grid)
    # last X in each row/column
    last_x_in_row: List[Optional[int]] = [None] * R
    for r in range(R):
        for c in range(C-1, -1, -1):
            if grid[r][c] == 'X':
                last_x_in_row[r] = c
                break
    last_x_in_col: List[Optional[int]] = [None] * C
    for c in range(C):
        for r in range(R-1, -1, -1):
            if grid[r][c] == 'X':
                last_x_in_col[c] = r
                break
    # intersections mask
    across_mask = [[False]*C for _ in range(R)]
    for (r, s, e) in across_runs:
        for c in range(s, e+1):
            across_mask[r][c] = True
    down_mask = [[False]*C for _ in range(R)]
    for (sr, er, c) in down_runs:
        for r in range(sr, er+1):
            down_mask[r][c] = True
    intersection_mask = [[across_mask[r][c] and down_mask[r][c] for c in range(C)] for r in range(R)]
    # down end positions (suffix constraint cells)
    down_end: Set[Tuple[int, int]] = set((er, c) for (sr, er, c) in down_runs)
    # across start positions (prefix constraint cells)
    across_start: Set[Tuple[int, int]] = set((r, s) for (r, s, e) in across_runs)
    return across_runs, down_runs, last_x_in_row, last_x_in_col, intersection_mask, down_end, across_start


def _guided_fill_across(grid: List[List[str]],
                        alphabet: List[str],
                        intersection_rule: int,
                        forbid_adjacent: bool,
                        row_vowel_even: bool,
                        col_cons_odd: bool,
                        diag_distinct: bool,
                        no_pal_across: bool,
                        prefix_set: Optional[List[str]],
                        suffix_set: Optional[List[str]]) -> Optional[Tuple[List[str], List[List[str]]]]:
    """
    Construct across words with backtracking under all constraints, filling the grid deterministically.
    Returns (across_words, filled_grid) or None if failed.
    """
    R, C = len(grid), len(grid[0]) if grid else 0
    across_runs, down_runs, last_x_in_row, last_x_in_col, intersection_mask, down_end, across_start = _compute_constraint_maps(grid)
    filled: List[List[Optional[str]]] = _grid_spaces_template(grid)
    row_vcnt = [0] * R  # count vowels in X cells per row
    col_ccnt = [0] * C  # count consonants in X cells per column
    diag_used: Set[str] = set()
    seen_words: Set[str] = set()

    alpha_set = set(alphabet)
    vowels = _VOWELS
    consonants = set(ch for ch in alpha_set if _is_consonant(ch))

    across_words: List[str] = []

    # Helper: get allowed letters for a position
    def allowed_letters_for(r: int, c: int, left_ch: Optional[str], is_first: bool, is_last_in_row: bool, is_last_in_col: bool) -> List[str]:
        allowed: Set[str] = set(alphabet)
        # intersection rule
        if intersection_rule == 1 and intersection_mask[r][c]:
            allowed &= vowels
        elif intersection_rule == 2 and intersection_mask[r][c]:
            allowed &= consonants
        # suffix of down words
        if suffix_set is not None and (r, c) in down_end:
            allowed &= set(suffix_set)
        # prefix of across words
        if prefix_set is not None and is_first:
            allowed &= set(prefix_set)
        # forbid adjacency
        if forbid_adjacent:
            if left_ch is not None:
                allowed.discard(left_ch)
            if r - 1 >= 0 and grid[r][c] == 'X' and grid[r-1][c] == 'X':
                up_ch = filled[r-1][c]
                if up_ch is not None and up_ch != ' ':
                    try:
                        allowed.remove(up_ch)  # type: ignore
                    except KeyError:
                        pass
        # diagonal distinct
        if diag_distinct and r == c and grid[r][c] == 'X':
            allowed -= diag_used
        # row vowel parity on the last X of the row
        if row_vowel_even and is_last_in_row:
            need_vowel = (row_vcnt[r] % 2 == 1)
            allowed = {ch for ch in allowed if (_is_vowel(ch) == need_vowel)}
        # column consonant parity on the last X of the column
        if col_cons_odd and is_last_in_col:
            # Need final odd => at last X, choose consonant iff current count is even
            need_consonant = (col_ccnt[c] % 2 == 0)
            allowed = {ch for ch in allowed if (_is_consonant(ch) == need_consonant)}
        return list(allowed)

    # Backtrack inside each across run
    for (r, s, e) in across_runs:
        L = e - s + 1
        word_chars: List[Optional[str]] = [None] * L
        # backtrack search with node budget
        node_budget = 3000  # prevent pathological blow-up
        success = False

        def dfs(pos: int) -> bool:
            nonlocal node_budget
            if node_budget <= 0:
                return False
            node_budget -= 1
            if pos == L:
                w = ''.join(ch for ch in word_chars if ch is not None)  # type: ignore
                if no_pal_across and _is_palindrome(w):
                    return False
                if w in seen_words:
                    return False
                return True
            c = s + pos
            left_ch = word_chars[pos-1] if pos > 0 else None
            is_first = (pos == 0)
            is_last_in_row = (last_x_in_row[r] == c)
            is_last_in_col = (last_x_in_col[c] == r)
            candidates = allowed_letters_for(r, c, left_ch, is_first, is_last_in_row, is_last_in_col)
            if not candidates:
                return False
            random.shuffle(candidates)
            for ch in candidates:
                # place
                word_chars[pos] = ch
                if _is_vowel(ch):
                    row_vcnt[r] += 1
                if _is_consonant(ch):
                    col_ccnt[c] += 1
                if diag_distinct and r == c and grid[r][c] == 'X':
                    diag_used.add(ch)
                filled[r][c] = ch
                if dfs(pos + 1):
                    return True
                # undo
                filled[r][c] = None
                if diag_distinct and r == c and ch in diag_used:
                    diag_used.discard(ch)
                if _is_vowel(ch):
                    row_vcnt[r] -= 1
                if _is_consonant(ch):
                    col_ccnt[c] -= 1
                word_chars[pos] = None
            return False

        if not dfs(0):
            return None

        w = ''.join(ch for ch in word_chars if ch is not None)  # type: ignore
        seen_words.add(w)
        across_words.append(w)

    # cast filled to List[List[str]]
    filled_str: List[List[str]] = [[' ' if filled[r][c] in (None, ' ') else str(filled[r][c]) for c in range(C)] for r in range(R)]
    return across_words, filled_str


# ---------------------------
# Generation
# ---------------------------

def _pick_prefix_suffix_sets(alphabet: List[str], on_prefix: bool, on_suffix: bool) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    prefix_set: Optional[List[str]] = None
    suffix_set: Optional[List[str]] = None
    if on_prefix:
        k = random.choice([1, 2])
        prefix_set = random.sample(alphabet, min(k, len(alphabet)))
    if on_suffix:
        k = random.choice([1, 2])
        suffix_set = random.sample(alphabet, min(k, len(alphabet)))
    return prefix_set, suffix_set


def generate_puzzle(rows: int,
                    cols: int,
                    across_min: int,
                    across_max: int,
                    down_min: int,
                    down_max: int,
                    alphabet: List[str],
                    intersection_rule: int,
                    forbid_adjacent: bool,
                    include_quota: bool,
                    row_vowel_even: bool,
                    col_cons_odd: bool,
                    diag_distinct: bool,
                    no_pal_across: bool,
                    prefix_rule_on: bool,
                    suffix_rule_on: bool) -> Dict[str, Any]:
    """
    Generate a full puzzle instance using guided construction to avoid excessive backtracking.
    Returns keys: grid, across, down, filled, json, rules_text, quota_letter (opt), quota_count (opt),
                  prefix_set (opt), suffix_set (opt)
    """
    # Prepare alphabet for feasibility
    effective_alphabet = _prepare_alphabet(alphabet, intersection_rule, row_vowel_even, col_cons_odd)
    # Choose prefix/suffix sets based on flags
    prefix_set, suffix_set = _pick_prefix_suffix_sets(effective_alphabet, prefix_rule_on, suffix_rule_on)

    max_global_attempts = 200
    for _ in range(max_global_attempts):
        # Generate a grid that satisfies run-length constraints
        try:
            grid = _generate_grid(rows, cols, across_min, across_max, down_min, down_max, max_attempts=2000)
        except RuntimeError:
            continue

        # Try to build across words with guidance
        for __ in range(120):
            guided = _guided_fill_across(
                grid=grid,
                alphabet=effective_alphabet,
                intersection_rule=intersection_rule,
                forbid_adjacent=forbid_adjacent,
                row_vowel_even=row_vowel_even,
                col_cons_odd=col_cons_odd,
                diag_distinct=diag_distinct,
                no_pal_across=no_pal_across,
                prefix_set=prefix_set,
                suffix_set=suffix_set
            )
            if guided is None:
                continue
            across_words, filled = guided
            # Compute down words
            down_words = _extract_down_words_from_filled(filled, grid)

            # Full rule checks (should pass due to guided construction; verify anyway)
            if not _check_intersection_rule(grid, filled, intersection_rule):
                continue
            if forbid_adjacent and not _check_no_adjacent_identical(filled):
                continue
            if row_vowel_even and not _check_row_vowel_even(filled, grid):
                continue
            if col_cons_odd and not _check_col_consonant_odd(filled, grid):
                continue
            if diag_distinct and not _check_diag_distinct(filled, grid):
                continue
            if suffix_set is not None:
                bad = False
                for w in down_words:
                    if len(w) == 0 or w[-1] not in suffix_set:
                        bad = True
                        break
                if bad:
                    continue

            quota_letter: Optional[str] = None
            quota_count: Optional[int] = None
            if include_quota:
                letters = [ch for row in filled for ch in row if ch != ' ']
                if not letters:
                    continue
                quota_letter = random.choice(letters)
                quota_count = _letter_count(filled, quota_letter)

            # Build rule text for description (no quotes), no fixed across order anymore
            parts = []
            # Intersection
            if intersection_rule == 1:
                parts.append('letters at every intersection must be vowels')
            elif intersection_rule == 2:
                parts.append('letters at every intersection must be consonants')
            else:
                parts.append('no special restriction at intersections')
            # Adjacent
            if forbid_adjacent:
                parts.append('no identical letters may be adjacent horizontally or vertically')
            else:
                parts.append('identical adjacent letters are allowed')
            # Row vowel even
            if row_vowel_even:
                parts.append('each row has an even number of vowels counted only in X cells')
            # Col consonant odd
            if col_cons_odd:
                parts.append('each column that contains X has an odd number of consonants counted only in X cells')
            # Diagonal distinct
            if diag_distinct:
                parts.append('letters on X cells along the main diagonal are all distinct')
            # No palindrome across
            if no_pal_across:
                parts.append('no across word is a palindrome')
            # Prefix and suffix sets
            if prefix_set is not None and len(prefix_set) > 0:
                parts.append('each across word starts with one of these letters ' + ','.join(prefix_set))
            if suffix_set is not None and len(suffix_set) > 0:
                parts.append('each down word ends with one of these letters ' + ','.join(suffix_set))
            # Quota
            if include_quota and quota_letter is not None and quota_count is not None:
                parts.append('the total number of letter ' + quota_letter + ' in the filled grid is exactly ' + str(quota_count))
            # Set semantics
            parts.append('the across words are an unordered set; use each exactly once to fill across X runs')
            parts.append('the down words are an unordered set; in the final grid, each down X run must match one of them and each is used once')
            rules_text = '; '.join(parts)

            # Shuffle order for display (sets)
            across_out = across_words[:]
            down_out = down_words[:]
            random.shuffle(across_out)
            random.shuffle(down_out)

            # Verify uniqueness under unordered-sets rule and run-length constraints
            if verify_unique_fill_sets(grid, across_out, down_out, filled,
                                       intersection_rule, forbid_adjacent,
                                       quota_letter, quota_count,
                                       row_vowel_even, col_cons_odd,
                                       prefix_set, suffix_set,
                                       diag_distinct, no_pal_across,
                                       across_min, across_max, down_min, down_max):
                res: Dict[str, Any] = {
                    'grid': grid,
                    'across': across_out,
                    'down': down_out,
                    'filled': filled,
                    'json': json.dumps(filled),
                    'rules_text': rules_text
                }
                if quota_letter is not None and quota_count is not None:
                    res['quota_letter'] = quota_letter
                    res['quota_count'] = quota_count
                if prefix_set is not None:
                    res['prefix_set'] = prefix_set
                if suffix_set is not None:
                    res['suffix_set'] = suffix_set
                return res
        # Retry with a new grid

    # As a last resort, raise to avoid producing inconsistent puzzles
    raise RuntimeError("Failed to generate a unique puzzle under the given constraints")