# kukurasu_4.py
# -----------------------------------------------------------------------------
# High-complexity generalized Kakurasu generator (reverse mode).
# function_1(n): generate a unique-solution instance, randomize rule families,
#                and produce a readable single-line rule_text including all necessary parameters
#                (explicitly listing row residues when applicable).
# function_2(grid): format a 2D list of '1'/'X' into a compact JSON string.
# Guarantees: non-trivial parity (if enabled), controlled clues, >=2 advanced rule families active,
#             injective row-weights modulo for uniqueness, and fast solving within ~3 minutes.
# -----------------------------------------------------------------------------

from typing import List, Tuple, Dict, Any
import random
import json
import math

def _choices_affine_params(mod_base: int) -> Tuple[int, int]:
    a_candidates = [a for a in range(1, max(2, mod_base)) if math.gcd(a, mod_base) == 1]
    a = random.choice(a_candidates) if a_candidates else 1
    b = random.randint(0, max(1, mod_base) - 1)
    return a, b

def _make_weights(n: int, mod_base: int, mode: str) -> List[int]:
    if mode == 'index':
        return list(range(1, n + 1))
    if mode == 'perm':
        w = list(range(1, n + 1))
        random.shuffle(w)
        return w
    a, b = _choices_affine_params(mod_base)
    return [((a * j + b) % mod_base) for j in range(1, n + 1)]

def _banned_col_diag(i: int, n: int, ban_mode: str) -> int:
    return i if ban_mode == 'main' else (n + 1 - i)

def _build_permutation(n: int, ban_mode: str) -> List[int]:
    cols = list(range(1, n + 1))
    rows = list(range(1, n + 1))
    random.shuffle(rows)
    assignment: List[Any] = [None] * n
    used = set()

    def backtrack(idx: int) -> bool:
        if idx == n:
            return True
        i = rows[idx]
        banned = _banned_col_diag(i, n, ban_mode)
        candidates = [c for c in cols if c not in used and c != banned]
        random.shuffle(candidates)
        for c in candidates:
            assignment[i - 1] = c
            used.add(c)
            if backtrack(idx + 1):
                return True
            used.remove(c)
            assignment[i - 1] = None
        return False

    for _ in range(80):
        random.shuffle(rows)
        assignment = [None] * n
        used.clear()
        if backtrack(0):
            return [int(assignment[i]) for i in range(n)]  # type: ignore

    perm = list(range(1, n + 1))
    random.shuffle(perm)
    for i in range(1, n + 1):
        if perm[i - 1] == _banned_col_diag(i, n, ban_mode):
            j = (i % n) + 1
            perm[i - 1], perm[j - 1] = perm[j - 1], perm[i - 1]
    return perm

def _pick_random_extra_bans(n: int, perm: List[int], ban_mode: str, include_band_ban: bool, band_radius: int) -> List[Tuple[int, int]]:
    banned = {(i, _banned_col_diag(i, n, ban_mode)) for i in range(1, n + 1)}
    solution_cells = {(i, perm[i - 1]) for i in range(1, n + 1)}

    if include_band_ban and band_radius > 0:
        for i in range(1, n + 1):
            center = _banned_col_diag(i, n, ban_mode)
            for dj in range(-band_radius, band_radius + 1):
                j = center + dj
                if 1 <= j <= n and (i, j) not in solution_cells:
                    banned.add((i, j))

    candidates = [(i, j) for i in range(1, n + 1) for j in range(1, n + 1)
                  if (i, j) not in solution_cells and (i, j) not in banned]
    random.shuffle(candidates)
    k_extra = random.randint(0, max(0, n // 3))
    banned.update(candidates[:k_extra])

    return sorted(banned)

def _make_groups(n: int, perm: List[int]) -> Tuple[int, List[int], List[int]]:
    while True:
        group_num = random.randint(2, min(4, n))
        group_id = [random.randint(1, group_num) for _ in range(n)]
        counts = [0] * group_num
        for i in range(1, n + 1):
            g = group_id[perm[i - 1] - 1]
            counts[g - 1] += 1
        if all(c > 0 for c in counts):
            return group_num, group_id, counts

def _make_row_links(n: int, perm: List[int], mod_base: int) -> Tuple[List[Tuple[int, int]], List[int], List[int], int]:
    alt_mod = random.randint(max(2, n), max(2, n + 6))
    mode = random.choice(['index', 'perm', 'affine'])
    alt_row_weights = _make_weights(n, alt_mod, mode)
    tries = 0
    while len({w % alt_mod for w in alt_row_weights}) != n and tries < 10:
        alt_row_weights = _make_weights(n, alt_mod, mode)
        tries += 1

    rows = list(range(1, n + 1))
    random.shuffle(rows)
    kmax = max(1, n // 2)
    pairs: List[Tuple[int, int]] = []
    idx = 0
    k = random.randint(1, kmax)
    while idx + 1 < n and len(pairs) < k:
        pairs.append((rows[idx], rows[idx + 1]))
        idx += 2

    targets: List[int] = []
    for (r1, r2) in pairs:
        j1 = perm[r1 - 1]
        j2 = perm[r2 - 1]
        val = (alt_row_weights[j1 - 1] + alt_row_weights[j2 - 1]) % alt_mod
        targets.append(val)

    return pairs, targets, alt_row_weights, alt_mod

def _make_parity(n: int, perm: List[int]) -> Tuple[List[int], List[int]]:
    while True:
        ones = random.randint(1, n - 1) if n > 1 else 1
        bm = [0] * n
        idxs = random.sample(range(n), ones)
        for k in idxs:
            bm[k] = 1
        if any(bm) and not all(bm):
            par = [bm[perm[i - 1] - 1] % 2 for i in range(1, n + 1)]
            return bm, par

def function_1(n: int) -> Dict[str, Any]:
    """
    Generate a high-complexity Kakurasu instance with guaranteed unique solution.
    Enforce: >=2 advanced rule families active among {column modulo, group counting, row links, parity};
             non-trivial parity when enabled; controlled clues; readable rule_text with explicit row residues.
    """
    assert n >= 2

    ban_mode = random.choice(['main', 'anti'])
    perm = _build_permutation(n, ban_mode)

    # Row-side modulus and weights (injective modulo for uniqueness)
    mod_base = n if random.random() < 0.6 else random.randint(n, n + 4)
    row_mode = random.choice(['index', 'perm', 'affine'])
    row_weights = _make_weights(n, mod_base, row_mode)
    while len({w % mod_base for w in row_weights}) != n:
        row_weights = _make_weights(n, mod_base, row_mode)
    # Row residues (explicitly listed for the player)
    row_res = [row_weights[perm[i - 1] - 1] % mod_base for i in range(1, n + 1)]

    # Column side (optional modulo)
    col_mode = random.choice(['index', 'perm', 'affine'])
    col_weights = _make_weights(n, mod_base, col_mode)
    inv_row_of_col = [0] * n
    for i in range(1, n + 1):
        inv_row_of_col[perm[i - 1] - 1] = i
    col_res = [col_weights[i - 1] % mod_base for i in inv_row_of_col]

    # Advanced rule toggles; ensure >=2 active
    include_col_mod = bool(random.getrandbits(1))
    include_group_count = bool(random.getrandbits(1))
    include_row_link = bool(random.getrandbits(1))
    include_parity = bool(random.getrandbits(1))
    while sum([include_col_mod, include_group_count, include_row_link, include_parity]) < 2:
        choice = random.choice([0, 1, 2, 3])
        if choice == 0:
            include_col_mod = True
        elif choice == 1:
            include_group_count = True
        elif choice == 2:
            include_row_link = True
        else:
            include_parity = True

    # Column cardinality and clues
    col_card_exact = bool(random.getrandbits(1))
    min_col_req = 1

    # Bans: diagonal + optional band + extras
    include_band_ban = bool(random.getrandbits(1))
    band_radius = random.randint(0, 1) if include_band_ban else 0
    banned_pairs = _pick_random_extra_bans(n, perm, ban_mode, include_band_ban, band_radius)

    # Controlled clues (<= n//4)
    k_force = random.randint(0, max(0, n // 4))
    force_rows = random.sample(range(1, n + 1), k_force) if k_force > 0 else []
    force_pairs = [(i, perm[i - 1]) for i in force_rows]

    # Group counting (ensure each group has ≥1 selected column)
    if include_group_count:
        group_num, group_id, group_counts = _make_groups(n, perm)
    else:
        group_num, group_id, group_counts = 0, [], []

    # Row links (at least one pair if enabled)
    if include_row_link:
        row_link_pairs, row_link_targets, alt_row_weights, alt_mod = _make_row_links(n, perm, mod_base)
    else:
        row_link_pairs, row_link_targets, alt_row_weights, alt_mod = [], [], [], 2

    # Parity (non-trivial if enabled)
    if include_parity:
        parity_bm, row_parity = _make_parity(n, perm)
    else:
        parity_bm, row_parity = [], []

    # Human-readable rule summary (single line, no double quotes) with explicit row residues
    def fmt_list(lst: List[int]) -> str:
        return "[" + ",".join(str(x) for x in lst) + "]"
    def fmt_pairs(pairs: List[Tuple[int,int]]) -> str:
        return "[" + ",".join(f"({i},{j})" for (i,j) in pairs) + "]"

    parts: List[str] = []
    parts.append("索引均从 1 开始, 坐标按 (行,列) 给出")
    parts.append(f"网格大小 n={n}, 模数 mod={mod_base}")
    parts.append(f"行权重按列编号={fmt_list(row_weights)}; 行余数={fmt_list(row_res)}; 行加权和为该行选中列的行权重之和后取模, 等于行余数")
    parts.append("每行恰有 1 个 1")
    parts.append(f"禁止填 1 的坐标={fmt_pairs(banned_pairs)}")
    parts.append(("每列恰有 1 个 1") if col_card_exact else (f"每列至少 {min_col_req} 个 1"))
    if include_col_mod:
        parts.append(f"列权重按行编号={fmt_list(col_weights)}; 列余数={fmt_list(col_res)}; 列加权和为该列选中行的列权重之和后取模, 等于列余数")
    else:
        parts.append("列加权取模约束未启用")
    if include_group_count:
        parts.append(f"列分组总数={group_num}; 分组标记按列={fmt_list(group_id)}; 各组需要的 1 的数量={fmt_list(group_counts)}")
    if include_row_link and len(row_link_pairs) > 0:
        pair_text = ";".join(f"(行{r1},行{r2})->{row_link_targets[idx]}" for idx,(r1,r2) in enumerate(row_link_pairs))
        parts.append(f"联合行权重按列={fmt_list(alt_row_weights)}; 联合模数={alt_mod}; 各行对目标值={pair_text}; 计算: 两行各自选中列的联合权重求和后取模, 等于对应目标值")
    if include_parity:
        parts.append(f"奇偶掩码按列={fmt_list(parity_bm)}; 各行奇偶值={fmt_list(row_parity)}; 计算: 每行对选中列的掩码值求和后对 2 取模, 等于该行奇偶值")
    if len(force_pairs) > 0:
        parts.append(f"已知为 1 的线索坐标={fmt_pairs(force_pairs)}")
    parts.append("答案格式: 输出 JSON 风格二维列表字符串, 如 [[X,1,...], ...], 每个元素为字符串 1 或 X")
    rule_text = "; ".join(parts) + "。"

    return {
        'ban_mode': ban_mode,
        'mod_base': mod_base,
        'perm': perm,
        'row_weights': row_weights,
        'col_weights': col_weights,
        'row_res': row_res,
        'col_res': col_res,
        'banned_pairs': banned_pairs,
        'include_col_mod': include_col_mod,
        'col_card_exact': col_card_exact,
        'min_col_req': min_col_req,
        'force_pairs': force_pairs,
        'include_group_count': include_group_count,
        'group_num': group_num,
        'group_id': group_id,
        'group_counts': group_counts,
        'include_row_link': include_row_link,
        'row_link_pairs': row_link_pairs,
        'alt_row_weights': alt_row_weights,
        'alt_mod': alt_mod,
        'row_link_targets': row_link_targets,
        'include_parity': include_parity,
        'parity_bm': parity_bm,
        'row_parity': row_parity,
        'rule_text': rule_text,
    }

def function_2(grid: List[List[str]]) -> str:
    sanitized = [[('1' if c == '1' else 'X') for c in row] for row in grid]
    return json.dumps(sanitized, ensure_ascii=False)