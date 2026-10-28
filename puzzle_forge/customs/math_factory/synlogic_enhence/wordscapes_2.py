# file: wordscapes_5.py
import random
import time
from typing import List, Dict, Tuple, Set, Optional

# --------------------------
# Public operators for YAML
# --------------------------
def join_list(lst: List[str]) -> str:
    """Join a list of strings with comma and space (用于题面渲染)."""
    return ', '.join(lst)

def build_unique_signature_puzzle(n: int) -> Dict[str, object]:
    """
    Build a letter-grid puzzle with unique solution and ensured reasoning depth:
      - bank: candidate strings (uppercase) of length n; includes base eco-themed words + derived column strings + random augmentations.
      - row_clues, col_clues: visible clues like 'R1 SIG=ABCD', 'C3 PRE2=TR', 'C2 SUF3=END'.
      - global_clues: compact global constraints strings, e.g., 'DIAGSIG=ABCD', 'ROW3_VOW=2', 'CORNERSIG=....', 'ANTI_VOW=...'.
      - diag_original, diag_shift: main diagonal raw string and Caesar+1.
      - anti_original, anti_shift: anti-diagonal raw string and Caesar+1.
    """
    if n not in (4, 5):
        raise ValueError("n must be 4 or 5")

    outer_attempts = 0
    # 扩大外层重试上限，提升稳定性
    max_outer_attempts = 120

    while outer_attempts < max_outer_attempts:
        outer_attempts += 1

        base_bank = _get_bank(n)
        # Construct a valid grid with distinct rows from bank; columns must be distinct
        try:
            rows = _build_valid_grid(n, base_bank, max_trials=50000)
        except RuntimeError:
            continue

        cols = [''.join(rows[i][j] for i in range(n)) for j in range(n)]

        # Augment bank: include all columns, publish as a unified list
        bank_out_set: Set[str] = set(w.upper() for w in base_bank if len(w) == n)
        for cw in cols:
            bank_out_set.add(cw.upper())
        bank_out = sorted(list(bank_out_set))

        diag_original = ''.join(rows[i][i] for i in range(n))
        diag_shift = caesar_shift_plus1(diag_original)
        anti_original = ''.join(rows[i][n - 1 - i] for i in range(n))
        anti_shift = caesar_shift_plus1(anti_original)

        # Initial strong clues: all SIG
        row_types: List[Tuple[str, Optional[int]]] = [('SIG', None) for _ in range(n)]
        col_types: List[Tuple[str, Optional[int]]] = [('SIG', None) for _ in range(n)]

        # Baseline global (we will add more)
        diag_sig_val = _signature(diag_original)
        base_global_specs: List[Tuple[str, tuple]] = [('DIAGSIG', (diag_sig_val,))]

        # First, randomized weakening while keeping uniqueness
        k_candidates = _k_candidates(n)
        weaken_pool = ['PRE', 'SUF'] if k_candidates else []
        attempts = 0
        max_attempts = 16
        while attempts < max_attempts and weaken_pool:
            attempts += 1
            mutated = False
            if random.random() < 0.5:
                idx = random.randrange(n)
                new_t = random.choice(weaken_pool)
                new_k = random.choice(k_candidates)
                old = row_types[idx]
                row_types[idx] = (f"{new_t}{new_k}", new_k)
                if _check_unique(n, bank_out, rows, row_types, col_types, base_global_specs, time_limit_sec=30):
                    mutated = True
                else:
                    row_types[idx] = old
            else:
                idx = random.randrange(n)
                new_t = random.choice(weaken_pool)
                new_k = random.choice(k_candidates)
                old = col_types[idx]
                col_types[idx] = (f"{new_t}{new_k}", new_k)
                if _check_unique(n, bank_out, rows, row_types, col_types, base_global_specs, time_limit_sec=30):
                    mutated = True
                else:
                    col_types[idx] = old
            if mutated and random.random() < 0.3:
                break

        # Enforce deeper clue structure: row≥2 non-SIG, col≥2 non-SIG, total≥4; ensure both PRE and SUF exist
        if not _enforce_min_non_sig(n, bank_out, rows, row_types, col_types, base_global_specs, min_row=2, min_col=2, min_total=4):
            continue
        if not _ensure_has_types(n, bank_out, rows, row_types, col_types, base_global_specs, need=('PRE', 'SUF')):
            continue

        # Eliminate trivial (显见) clues for all types: enforce each clue has >=2 candidates in bank_out
        if not _eliminate_trivial_all(n, bank_out, rows, row_types, col_types, base_global_specs):
            continue

        # Try to add at least one extra global clue beyond DIAGSIG (optionally up to 2 total extra)
        global_specs: List[Tuple[str, tuple]] = list(base_global_specs)
        global_clues: List[str] = [_format_global_clue_display(('DIAGSIG', (diag_sig_val,)))]

        corners = ''.join([rows[0][0], rows[0][n - 1], rows[n - 1][0], rows[n - 1][n - 1]])
        corner_sig_val = _signature(corners)
        anti_vow_val = _count_vowels(anti_original)

        row_vow_pairs = []
        for i in range(n):
            vc = _count_vowels(rows[i])
            if 0 < vc < n:
                row_vow_pairs.append((i, vc))
        random.shuffle(row_vow_pairs)

        candidates: List[Tuple[str, tuple]] = [('CORNERSIG', (corner_sig_val,)), ('ANTI_VOW', (anti_vow_val,))]
        for i, vc in row_vow_pairs[:2]:
            candidates.append(('ROW_VOW', (i, vc)))
        random.shuffle(candidates)

        added_count = 0
        for spec in candidates:
            if len(global_specs) >= 3:  # allow up to 2 extra globals total
                break
            try_specs = global_specs + [spec]
            if _check_unique(n, bank_out, rows, row_types, col_types, try_specs, time_limit_sec=30):
                global_specs.append(spec)
                global_clues.append(_format_global_clue_display(spec))
                added_count += 1

        # Must have at least one extra global clue
        if added_count < 1:
            continue

        # After adding globals, ensure again: (1) uniqueness; (2) no-singleton clues; (3) min non-SIG and type coverage
        if not _check_unique(n, bank_out, rows, row_types, col_types, global_specs, time_limit_sec=30):
            continue
        if not _eliminate_trivial_all(n, bank_out, rows, row_types, col_types, global_specs):
            continue
        if not _enforce_min_non_sig(n, bank_out, rows, row_types, col_types, global_specs, min_row=2, min_col=2, min_total=4):
            continue
        if not _ensure_has_types(n, bank_out, rows, row_types, col_types, global_specs, need=('PRE', 'SUF')):
            continue
        if not _check_unique(n, bank_out, rows, row_types, col_types, global_specs, time_limit_sec=30):
            continue

        # Build and return display clues
        cols = [''.join(rows[i][j] for i in range(n)) for j in range(n)]
        row_clues = [_format_clue_display(i, rows[i], row_types[i]) for i in range(n)]
        col_clues = [_format_clue_display(j, cols[j], col_types[j], is_row=False) for j in range(n)]

        return {
            'bank': bank_out,
            'row_clues': row_clues,
            'col_clues': col_clues,
            'global_clues': global_clues,
            'diag_original': diag_original,
            'diag_shift': diag_shift,
            'anti_original': anti_original,
            'anti_shift': anti_shift
        }

    # As a last resort, raise error if unable to construct within attempts
    raise RuntimeError("Failed to construct a uniquely solvable puzzle with strengthened depth")

# --------------------------
# Internal helpers
# --------------------------
_VOWELS = set(list("AEIOU"))

def _k_candidates(n: int) -> List[int]:
    """All legal k for PRE/SUF: 1..n-1."""
    return [k for k in range(1, n) if 1 <= k < n]

def _format_clue_display(idx: int, word: str, clue: Tuple[str, Optional[int]], is_row: bool = True) -> str:
    """
    Render a single row//col clue line like:
      R1 SIG=ABCD
      C3 PRE2=TR
      C2 SUF3=END
    """
    label = 'R' if is_row else 'C'
    ctype, k = clue
    if ctype == 'SIG':
        val = _signature(word)
        return f"{label}{idx+1} SIG={val}"
    elif ctype.startswith('PRE'):
        k = int(ctype[3:]) if k is None else k
        val = word[:k]
        return f"{label}{idx+1} PRE{k}={val}"
    elif ctype.startswith('SUF'):
        k = int(ctype[3:]) if k is None else k
        val = word[-k:]
        return f"{label}{idx+1} SUF{k}={val}"
    else:
        raise ValueError("Unknown clue type")

def _format_global_clue_display(spec: Tuple[str, tuple]) -> str:
    """
    Render a global clue:
      DIAGSIG=ABCD
      ANTI_VOW=2
      ROW3_VOW=2
      CORNERSIG=ABCD
    """
    typ, val = spec
    if typ == 'DIAGSIG':
        return f"DIAGSIG={val[0]}"
    if typ == 'ANTI_VOW':
        return f"ANTI_VOW={val[0]}"
    if typ == 'CORNERSIG':
        return f"CORNERSIG={val[0]}"
    if typ == 'ROW_VOW':
        i, cnt = val
        return f"ROW{i+1}_VOW={cnt}"
    raise ValueError("Unknown global spec type")

def _signature(word: str) -> str:
    """Sorted-letter multiset signature, uppercase."""
    return ''.join(sorted(word.upper()))

def caesar_shift_plus1(s: str) -> str:
    """Shift letters forward by 1 in Caesar cipher, wrapping Z->A. Output uppercase."""
    res_chars = []
    for ch in s:
        if 'A' <= ch <= 'Z':
            shifted = chr(((ord(ch) - ord('A') + 1) % 26) + ord('A'))
            res_chars.append(shifted)
        elif 'a' <= ch <= 'z':
            shifted = chr(((ord(ch) - ord('a') + 1) % 26) + ord('A'))
            res_chars.append(shifted)
        else:
            res_chars.append(ch)
    return ''.join(res_chars)

def _count_vowels(s: str) -> int:
    return sum(1 for ch in s if ch in _VOWELS)

def _biased_letter() -> str:
    """Return a letter with slight bias toward common English letters and vowels to create more collisions."""
    pool = "EEEAAARRIIONTTLSUCDPMGHBKFYWVJXZ"
    return random.choice(pool)

def _rand_word_n(n: int) -> str:
    return ''.join(_biased_letter() for _ in range(n))

def _add_signature_cluster(store: Set[str], n: int, count: int = 3):
    """Create 'count' distinct permutations sharing the same signature."""
    base = [_biased_letter() for _ in range(n)]
    for _ in range(count * 2):
        random.shuffle(base)
        w = ''.join(base)
        store.add(w)

def _add_prefix_cluster(store: Set[str], n: int, k: int, count: int = 4):
    """Create 'count' words sharing same prefix of length k."""
    pref = ''.join(_biased_letter() for _ in range(k))
    for _ in range(count * 2):
        suf = ''.join(_biased_letter() for _ in range(n - k))
        store.add((pref + suf))

def _add_suffix_cluster(store: Set[str], n: int, k: int, count: int = 4):
    """Create 'count' words sharing same suffix of length k."""
    suf = ''.join(_biased_letter() for _ in range(k))
    for _ in range(count * 2):
        pref = ''.join(_biased_letter() for _ in range(n - k))
        store.add((pref + suf))

def _get_bank(n: int) -> List[str]:
    """
    Return a candidate bank for length n as uppercase strings.
    基础生态词汇 + 随机增强（包含 signature/prefix/suffix 簇），以提高“非显见线索（候选≥2）”的可达性。
    """
    base = []
    if n == 4:
        base = [
            'TREE','SEED','SOIL','RAIN','WIND','LAKE','MOSS','LEAF','REEF','DUNE',
            'FLOW','WAVE','FISH','BIRD','DEER','WOLF','FROG','REED','PEAT','LOAM',
            'SAND','SILT','CLAY','ALGA','FERN','POND','COVE','TIDE','SEAS','COAL'
        ]
        target_size = 160
    elif n == 5:
        base = [
            'BIOME','FLORA','FAUNA','RIVER','CORAL','DELTA','OZONE','EARTH','WATER','OCEAN',
            'TREES','SEEDS','ALGAE','GRASS','REUSE','CLEAN','PLANT','CYCLE','SOILS','WINDS',
            'RAINS','GREEN','LEAFY','REEFS','CANAL','SWAMP','TIDES','SHORE','BEACH','COAST',
            'HUMUS','LOESS','PONDS','FJORD','RIDGE'
        ]
        target_size = 220
    else:
        raise ValueError("Unsupported length")

    store: Set[str] = set(w for w in base if len(w) == n)

    # 先加入一定量的随机串
    while len(store) < target_size // 3:
        store.add(_rand_word_n(n))

    # 再制造若干 signature/prefix/suffix 簇
    for _ in range(12):
        _add_signature_cluster(store, n, count=3)
    for _ in range(10):
        k = random.choice(_k_candidates(n))
        _add_prefix_cluster(store, n, k=k, count=4)
    for _ in range(10):
        k = random.choice(_k_candidates(n))
        _add_suffix_cluster(store, n, k=k, count=4)

    # 最后补齐到目标体量
    while len(store) < target_size:
        r = random.random()
        if r < 0.33:
            _add_signature_cluster(store, n, count=2)
        elif r < 0.66:
            k = random.choice(_k_candidates(n))
            _add_prefix_cluster(store, n, k=k, count=3)
        else:
            k = random.choice(_k_candidates(n))
            _add_suffix_cluster(store, n, k=k, count=3)
        if len(store) > target_size + 30:
            break

    bank = sorted(list(store))[:target_size]
    return bank

def _build_valid_grid(n: int, bank: List[str], max_trials: int = 2000) -> List[str]:
    """
    Construct an n x n grid as list of row strings from bank so that:
      - every row is distinct and belongs to the bank (uppercased)
      - every column string is distinct (columns need not belong to the base bank here)
    """
    bank = [w.upper() for w in bank if len(w) == n]
    if len(set(bank)) < n:
        raise RuntimeError("Bank too small for constructing rows")

    for _ in range(max_trials):
        rows = random.sample(bank, n)
        if len(set(rows)) != n:
            continue
        cols = [''.join(rows[i][j] for i in range(n)) for j in range(n)]
        if len(set(cols)) != n:
            continue
        return rows
    raise RuntimeError("Failed to build a valid grid")

def _derive_value(word: str, clue: Tuple[str, Optional[int]]) -> str:
    """Compute displayed value for a given word under the clue."""
    ctype, k = clue
    if ctype == 'SIG':
        return _signature(word)
    if ctype.startswith('PRE'):
        k = int(ctype[3:]) if k is None else k
        return word[:k]
    if ctype.startswith('SUF'):
        k = int(ctype[3:]) if k is None else k
        return word[-k:]
    raise ValueError("Unknown clue type")

def _all_prefixes(words: List[str], n: int) -> List[Set[str]]:
    """For each length 1..n, build a set of prefixes present in the word list."""
    prefix_sets = [set() for _ in range(n+1)]
    for w in words:
        for k in range(1, n+1):
            prefix_sets[k].add(w[:k])
    return prefix_sets

def _letter_count_map(sig: str) -> Dict[str, int]:
    m: Dict[str, int] = {}
    for ch in sig:
        m[ch] = m.get(ch, 0) + 1
    return m

def _count_solutions_from_clues(n: int,
                                bank: List[str],
                                row_specs: List[Tuple[str, Optional[int], str]],
                                col_specs: List[Tuple[str, Optional[int], str]],
                                global_specs: List[Tuple[str, tuple]],
                                stop_after: int = 2,
                                time_limit_sec: int = 30) -> Tuple[int, Optional[List[str]]]:
    """
    Count valid grids consistent with:
      - row_specs: per row (type, k, displayed_value)
      - col_specs: per column (type, k, displayed_value)
      - global_specs: list of ('DIAGSIG',(sig,)) or ('ANTI_VOW',(k,)) or ('CORNERSIG',(sig,))
                      or ('ROW_VOW',(i,k))
      - rows/cols drawn from augmented bank, rows distinct, columns distinct
    Returns (solution_count, one_solution_rows_if_found)
    Early-stops after reaching 'stop_after' solutions or time limit.
    """
    start_time = time.time()
    bank = [w.upper() for w in bank if len(w) == n]

    # Build candidate sets per row based on clues
    row_cands: List[List[str]] = []
    for (ctype, k, val) in row_specs:
        if ctype == 'SIG':
            cands = [w for w in bank if _signature(w) == val]
        elif ctype.startswith('PRE'):
            kk = int(ctype[3:]) if k is None else k
            cands = [w for w in bank if w[:kk] == val]
        elif ctype.startswith('SUF'):
            kk = int(ctype[3:]) if k is None else k
            cands = [w for w in bank if w[-kk:] == val]
        else:
            cands = []
        row_cands.append(cands)

    # Build candidate sets per column based on clues
    col_cands: List[List[str]] = []
    for (ctype, k, val) in col_specs:
        if ctype == 'SIG':
            cands = [w for w in bank if _signature(w) == val]
        elif ctype.startswith('PRE'):
            kk = int(ctype[3:]) if k is None else k
            cands = [w for w in bank if w[:kk] == val]
        elif ctype.startswith('SUF'):
            kk = int(ctype[3:]) if k is None else k
            cands = [w for w in bank if w[-kk:] == val]
        else:
            cands = []
        col_cands.append(cands)

    if any(len(c) == 0 for c in row_cands) or any(len(c) == 0 for c in col_cands):
        return 0, None

    # Precompute column prefix sets and candidate sets for pruning
    col_prefix_sets = []
    col_cand_sets = []
    for cset in col_cands:
        col_prefix_sets.append(_all_prefixes(cset, n))
        col_cand_sets.append(set(cset))

    # Use most-constrained-first row assignment to maximize pruning
    order = sorted(range(n), key=lambda i: len(row_cands[i]))

    grid_rows = [''] * n
    used_rows: Set[str] = set()
    solutions = 0
    one_solution_rows: Optional[List[str]] = None

    # Extract fast global constraints maps
    row_vow_req: Dict[int, int] = {}
    diag_sig_req: Optional[str] = None
    corner_sig_req: Optional[str] = None
    anti_vow_req: Optional[int] = None
    for typ, val in global_specs:
        if typ == 'ROW_VOW':
            i, k = val
            row_vow_req[i] = k
        elif typ == 'DIAGSIG':
            diag_sig_req = val[0]
        elif typ == 'CORNERSIG':
            corner_sig_req = val[0]
        elif typ == 'ANTI_VOW':
            anti_vow_req = val[0]

    diag_target_count = _letter_count_map(diag_sig_req) if diag_sig_req is not None else None
    corner_target_count = _letter_count_map(corner_sig_req) if corner_sig_req is not None else None

    def diag_partial_ok(i_row: int, w_row: str, true_row_index: int) -> bool:
        if diag_target_count is None:
            return True
        cnt: Dict[str, int] = {}
        for pos_before in range(len(order)):
            idx = order[pos_before]
            if not grid_rows[idx]:
                break
            ch = grid_rows[idx][idx]
            cnt[ch] = cnt.get(ch, 0) + 1
        ch_now = w_row[true_row_index]
        cnt[ch_now] = cnt.get(ch_now, 0) + 1
        for ch, c in cnt.items():
            if c > diag_target_count.get(ch, 0):
                return False
        return True

    def corners_partial_ok(i_row_order_pos: int, w_row: str, true_row_index: int) -> bool:
        if corner_target_count is None:
            return True
        known: List[str] = []
        if true_row_index == 0:
            top = w_row
            known.append(top[0])
            known.append(top[len(w_row)-1])
        elif grid_rows[0]:
            top = grid_rows[0]
            known.append(top[0])
            known.append(top[len(top)-1])
        if true_row_index == len(w_row)-1:
            bot = w_row
            known.append(bot[0])
            known.append(bot[len(w_row)-1])
        elif grid_rows[len(w_row)-1]:
            bot = grid_rows[len(w_row)-1]
            known.append(bot[0])
            known.append(bot[len(bot)-1])
        cnt: Dict[str, int] = {}
        for ch in known:
            cnt[ch] = cnt.get(ch, 0) + 1
            if cnt[ch] > corner_target_count.get(ch, 0):
                return False
        if len(known) == 4:
            if _signature(''.join(known)) != ''.join(sorted(''.join([k * corner_target_count[k] for k in corner_target_count]))):
                return False
        return True

    def anti_vow_partial_ok(w_row: str, true_row_index: int) -> bool:
        if anti_vow_req is None:
            return True
        curr = 0
        for idx in range(n):
            if not grid_rows[idx]:
                continue
            ch = grid_rows[idx][n-1-idx]
            if ch in _VOWELS:
                curr += 1
        ch_now = w_row[n-1-true_row_index]
        if ch_now in _VOWELS:
            curr += 1
        assigned = sum(1 for r in grid_rows if r)
        remaining = n - (assigned + 1)
        if curr > anti_vow_req:
            return False
        if curr + remaining < anti_vow_req:
            return False
        return True

    def backtrack(pos: int):
        nonlocal solutions, one_solution_rows
        if time.time() - start_time > time_limit_sec:
            solutions = stop_after
            return
        if solutions >= stop_after:
            return
        if pos == n:
            cols_now = [''.join(grid_rows[i][j] for i in range(n)) for j in range(n)]
            for j, cword in enumerate(cols_now):
                if cword not in col_cand_sets[j]:
                    return
            if len(set(cols_now)) != n:
                return
            if diag_sig_req is not None:
                diag = ''.join(grid_rows[i][i] for i in range(n))
                if _signature(diag) != diag_sig_req:
                    return
            if corner_sig_req is not None:
                corners_full = ''.join([grid_rows[0][0], grid_rows[0][n - 1], grid_rows[n - 1][0], grid_rows[n - 1][n - 1]])
                if _signature(corners_full) != corner_sig_req:
                    return
            if anti_vow_req is not None:
                anti = ''.join(grid_rows[i][n - 1 - i] for i in range(n))
                if _count_vowels(anti) != anti_vow_req:
                    return

            solutions += 1
            if solutions == 1:
                one_solution_rows = grid_rows[:]
            return

        i = order[pos]
        for w in row_cands[i]:
            if w in used_rows:
                continue
            if i in row_vow_req and _count_vowels(w) != row_vow_req[i]:
                continue
            if not diag_partial_ok(pos, w, i):
                continue
            if not anti_vow_partial_ok(w, i):
                continue
            if not corners_partial_ok(pos, w, i):
                continue
            ok = True
            for j in range(n):
                prefix_str = ''.join([(w[j] if order[rpos] == i else grid_rows[order[rpos]][j]) for rpos in range(pos+1)])
                plen = len(prefix_str)
                if prefix_str not in col_prefix_sets[j][plen]:
                    ok = False
                    break
            if not ok:
                continue
            grid_rows[i] = w
            used_rows.add(w)
            backtrack(pos + 1)
            if solutions >= stop_after:
                return
            grid_rows[i] = ''
            used_rows.remove(w)

    backtrack(0)
    return solutions, one_solution_rows

def _check_unique(n: int,
                  bank: List[str],
                  rows: List[str],
                  row_types: List[Tuple[str, Optional[int]]],
                  col_types: List[Tuple[str, Optional[int]]],
                  global_specs: List[Tuple[str, tuple]],
                  time_limit_sec: int = 30) -> bool:
    """Compute visible values per clue type and verify uniqueness using row/col/global clues."""
    cols = [''.join(rows[i][j] for i in range(n)) for j in range(n)]
    row_specs = []
    for i in range(n):
        ctype, k = row_types[i]
        val = _derive_value(rows[i], (ctype, k))
        row_specs.append((ctype, k, val))
    col_specs = []
    for j in range(n):
        ctype, k = col_types[j]
        val = _derive_value(cols[j], (ctype, k))
        col_specs.append((ctype, k, val))
    cnt, _ = _count_solutions_from_clues(n, bank, row_specs, col_specs, global_specs, stop_after=2, time_limit_sec=time_limit_sec)
    return cnt == 1

def _enforce_min_non_sig(n: int,
                         bank: List[str],
                         rows: List[str],
                         row_types: List[Tuple[str, Optional[int]]],
                         col_types: List[Tuple[str, Optional[int]]],
                         global_specs: List[Tuple[str, tuple]],
                         min_row: int,
                         min_col: int,
                         min_total: int) -> bool:
    """Ensure at least min_row/min_col/min_total non-SIG clues by converting SIG to PRE/SUF if possible while keeping uniqueness."""
    def count_non_sig():
        nr = sum(1 for t, _ in row_types if t != 'SIG')
        nc = sum(1 for t, _ in col_types if t != 'SIG')
        return nr, nc, nr + nc

    k_candidates = _k_candidates(n)
    if not k_candidates:
        return False

    def try_convert_index(i: int, is_row: bool) -> bool:
        types_to_try = []
        random.shuffle(k_candidates)
        for kk in k_candidates:
            types_to_try.append(('PRE', kk))
        for kk in k_candidates:
            types_to_try.append(('SUF', kk))
        random.shuffle(types_to_try)

        for typ, kk in types_to_try:
            if is_row:
                old = row_types[i]
                row_types[i] = (f"{typ}{kk}", kk)
                if _check_unique(n, bank, rows, row_types, col_types, global_specs, time_limit_sec=30):
                    return True
                row_types[i] = old
            else:
                old = col_types[i]
                col_types[i] = (f"{typ}{kk}", kk)
                if _check_unique(n, bank, rows, row_types, col_types, global_specs, time_limit_sec=30):
                    return True
                col_types[i] = old
        return False

    trials = 0
    max_trials = 60
    while trials < max_trials:
        trials += 1
        nr, nc, tot = count_non_sig()
        if nr >= min_row and nc >= min_col and tot >= min_total:
            return True
        targets: List[Tuple[bool, int]] = []
        if nr < min_row:
            targets += [(True, i) for i, (t, _) in enumerate(row_types) if t == 'SIG']
        if nc < min_col:
            targets += [(False, j) for j, (t, _) in enumerate(col_types) if t == 'SIG']
        if not targets and tot < min_total:
            targets += [(True, i) for i, (t, _) in enumerate(row_types) if t == 'SIG']
            targets += [(False, j) for j, (t, _) in enumerate(col_types) if t == 'SIG']
        if not targets:
            return False
        random.shuffle(targets)
        done = False
        for is_row, idx in targets:
            if try_convert_index(idx, is_row):
                done = True
                break
        if not done:
            break
    nr, nc, tot = count_non_sig()
    return nr >= min_row and nc >= min_col and tot >= min_total

def _ensure_has_types(n: int,
                      bank: List[str],
                      rows: List[str],
                      row_types: List[Tuple[str, Optional[int]]],
                      col_types: List[Tuple[str, Optional[int]]],
                      global_specs: List[Tuple[str, tuple]],
                      need: Tuple[str, str]) -> bool:
    """Ensure both types in 'need' (e.g., PRE and SUF) exist across row+col clues."""
    def has_type(target: str) -> bool:
        return any(t.startswith(target) for t, _ in (row_types + col_types))
    if all(has_type(t) for t in need):
        return True
    k_candidates = _k_candidates(n)
    if not k_candidates:
        return False

    def try_force_type(typ: str, is_row: bool) -> bool:
        indices = list(range(n))
        random.shuffle(indices)
        for idx in indices:
            if is_row:
                old = row_types[idx]
                if old[0] == 'SIG':
                    kk = random.choice(k_candidates)
                    row_types[idx] = (f"{typ}{kk}", kk)
                    if _check_unique(n, bank, rows, row_types, col_types, global_specs, time_limit_sec=30):
                        return True
                    row_types[idx] = old
            else:
                old = col_types[idx]
                if old[0] == 'SIG':
                    kk = random.choice(k_candidates)
                    col_types[idx] = (f"{typ}{kk}", kk)
                    if _check_unique(n, bank, rows, row_types, col_types, global_specs, time_limit_sec=30):
                        return True
                    col_types[idx] = old
        return False

    ok = True
    for t in need:
        if not has_type(t):
            ok = try_force_type(t, True) or try_force_type(t, False)
            if not ok:
                break
    return ok

def _cand_count_in_bank(bank: List[str], n: int, ctype: str, k: Optional[int], val: str) -> int:
    bank = [w for w in bank if len(w) == n]
    if ctype == 'SIG':
        return sum(1 for w in bank if _signature(w) == val)
    elif ctype.startswith('PRE'):
        kk = int(ctype[3:]) if k is None else k
        return sum(1 for w in bank if w[:kk] == val)
    elif ctype.startswith('SUF'):
        kk = int(ctype[3:]) if k is None else k
        return sum(1 for w in bank if w[-kk:] == val)
    return 0

def _eliminate_trivial_all(n: int,
                           bank: List[str],
                           rows: List[str],
                           row_types: List[Tuple[str, Optional[int]]],
                           col_types: List[Tuple[str, Optional[int]]],
                           global_specs: List[Tuple[str, tuple]]) -> bool:
    """
    Ensure every row/column clue individually has >=2 candidates in bank by adjusting types/k if necessary,
    while preserving uniqueness. Will try switching between PRE/SUF and varying k in 1..n-1, fallback SIG if needed,
    but still require candidate>=2. Returns True if successful; otherwise False.
    """
    k_candidates = _k_candidates(n)
    if not k_candidates:
        return False

    def specs_from_types() -> Tuple[List[Tuple[str, Optional[int], str]], List[Tuple[str, Optional[int], str]]]:
        cols_now = [''.join(rows[i][j] for i in range(n)) for j in range(n)]
        row_specs_local = []
        for i in range(n):
            ctype, kk = row_types[i]
            val = _derive_value(rows[i], (ctype, kk))
            row_specs_local.append((ctype, kk, val))
        col_specs_local = []
        for j in range(n):
            ctype, kk = col_types[j]
            val = _derive_value(cols_now[j], (ctype, kk))
            col_specs_local.append((ctype, kk, val))
        return row_specs_local, col_specs_local

    tries = 0
    max_tries = 80
    while tries < max_tries:
        tries += 1
        changed = False
        row_specs, col_specs = specs_from_types()

        # Repair rows
        for i in range(n):
            ctype, kk, val = row_specs[i]
            cc = _cand_count_in_bank(bank, n, ctype, kk, val)
            if cc <= 1:
                attempts: List[Tuple[str, Optional[int]]] = []
                for kx in k_candidates:
                    attempts.append((f"PRE{kx}", kx))
                for kx in k_candidates:
                    attempts.append((f"SUF{kx}", kx))
                attempts.append(('SIG', None))
                random.shuffle(attempts)
                old = row_types[i]
                success = False
                for new_t, new_k in attempts:
                    row_types[i] = (new_t, new_k)
                    new_val = _derive_value(rows[i], (new_t, new_k))
                    new_cc = _cand_count_in_bank(bank, n, new_t, new_k, new_val)
                    if new_cc >= 2 and _check_unique(n, bank, rows, row_types, col_types, global_specs, time_limit_sec=30):
                        success = True
                        changed = True
                        break
                    row_types[i] = old
                if not success:
                    return False

        # Repair columns
        cols_now = [''.join(rows[r][c] for r in range(n)) for c in range(n)]
        for j in range(n):
            ctype, kk, val = col_specs[j]
            cc = _cand_count_in_bank(bank, n, ctype, kk, val)
            if cc <= 1:
                attempts: List[Tuple[str, Optional[int]]] = []
                for kx in k_candidates:
                    attempts.append((f"PRE{kx}", kx))
                for kx in k_candidates:
                    attempts.append((f"SUF{kx}", kx))
                attempts.append(('SIG', None))
                random.shuffle(attempts)
                old = col_types[j]
                success = False
                for new_t, new_k in attempts:
                    col_types[j] = (new_t, new_k)
                    new_val = _derive_value(cols_now[j], (new_t, new_k))
                    new_cc = _cand_count_in_bank(bank, n, new_t, new_k, new_val)
                    if new_cc >= 2 and _check_unique(n, bank, rows, row_types, col_types, global_specs, time_limit_sec=30):
                        success = True
                        changed = True
                        break
                    col_types[j] = old
                if not success:
                    return False

        if not changed:
            break

    # Final verify all clues have >=2 candidates
    row_specs, col_specs = specs_from_types()
    for ctype, kk, val in row_specs:
        if _cand_count_in_bank(bank, n, ctype, kk, val) <= 1:
            return False
    for ctype, kk, val in col_specs:
        if _cand_count_in_bank(bank, n, ctype, kk, val) <= 1:
            return False
    return True

# --------------------------
# End of file
# --------------------------