# futoshiki_0.py
# 自定义算子：Futoshiki 可变规则生成与格式化工具集（进阶增强版，统一随机源与线索上限控制）
from typing import List, Tuple, Dict, Any, Optional, Set
import math
import random

try:
    from z3 import Solver, Int, And, Or, Distinct, sat
except Exception as e:
    raise RuntimeError("z3-solver is required for Futoshiki generation. Please install 'z3-solver'.") from e


# -------------------------------
# 基础工具：拉丁方与相邻对
# -------------------------------
def _make_base_latin_square(n: int, rng: random.Random) -> List[List[int]]:
    base = [[((i + j) % n) + 1 for j in range(n)] for i in range(n)]
    rows = list(range(n))
    cols = list(range(n))
    rng.shuffle(rows)
    rng.shuffle(cols)
    grid = [[base[rows[i]][cols[j]] for j in range(n)] for i in range(n)]
    mapping = list(range(1, n + 1))
    rng.shuffle(mapping)
    remap = {k: mapping[k - 1] for k in range(1, n + 1)}
    for i in range(n):
        for j in range(n):
            grid[i][j] = remap[grid[i][j]]
    return grid


def _adjacent_pairs_1_based(n: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    pairs = []
    # 水平相邻（同一行，列 j 与 j+1）
    for i in range(1, n + 1):
        for j in range(1, n):
            pairs.append(((i, j), (i, j + 1)))
    # 垂直相邻（同一列，行 i 与 i+1）
    for i in range(1, n):
        for j in range(1, n + 1):
            pairs.append(((i, j), (i + 1, j)))
    return pairs


def _ineq_direction_from_solution(sol_grid: List[List[int]],
                                  a: Tuple[int, int],
                                  b: Tuple[int, int]) -> str:
    ai, aj = a[0] - 1, a[1] - 1
    bi, bj = b[0] - 1, b[1] - 1
    va = sol_grid[ai][aj]
    vb = sol_grid[bi][bj]
    return 'gt' if va > vb else 'lt'


def _all_cells_1_based(n: int) -> List[Tuple[int, int]]:
    return [(i, j) for i in range(1, n + 1) for j in range(1, n + 1)]


def _value_at(sol: List[List[int]], c: Tuple[int, int]) -> int:
    return sol[c[0] - 1][c[1] - 1]


# -------------------------------
# 相邻遍历与路径生成（无重复）
# -------------------------------
def _neighbors_orth_1_based(i: int, j: int, n: int) -> List[Tuple[int, int]]:
    res = []
    for di, dj in [(1,0),(-1,0),(0,1),(0,-1)]:
        ni, nj = i + di, j + dj
        if 1 <= ni <= n and 1 <= nj <= n:
            res.append((ni, nj))
    return res


def _random_path_unique_orth(n: int, length: int, rng: random.Random, max_tries: int = 200) -> Optional[List[Tuple[int, int]]]:
    # 生成不含重复格的相邻路径；如遇死路则重启
    for _ in range(max_tries):
        i = rng.randint(1, n)
        j = rng.randint(1, n)
        path = [(i, j)]
        used = {(i, j)}
        ok = True
        for _t in range(length - 1):
            nbrs = _neighbors_orth_1_based(path[-1][0], path[-1][1], n)
            nbrs = [c for c in nbrs if c not in used]
            if not nbrs:
                ok = False
                break
            nxt = rng.choice(nbrs)
            path.append(nxt)
            used.add(nxt)
        if ok and len(path) == length:
            return path
    return None


# -------------------------------
# 非显见预填选择器（每行/列最多 n-2 个预填）
# -------------------------------
def _select_givens_nontrivial(n: int,
                              sol: List[List[int]],
                              target_count: int,
                              rng: random.Random,
                              row_max: Optional[int] = None,
                              col_max: Optional[int] = None) -> Dict[Tuple[int,int], int]:
    if row_max is None:
        row_max = max(0, n - 2)
    if col_max is None:
        col_max = max(0, n - 2)
    all_cells = _all_cells_1_based(n)
    rng.shuffle(all_cells)
    row_counts = {i: 0 for i in range(1, n + 1)}
    col_counts = {j: 0 for j in range(1, n + 1)}
    chosen: List[Tuple[int,int]] = []
    for c in all_cells:
        i, j = c
        if row_counts[i] >= row_max or col_counts[j] >= col_max:
            continue
        chosen.append(c)
        row_counts[i] += 1
        col_counts[j] += 1
        if len(chosen) >= target_count:
            break
    # 若未达到目标数量，尽量补充但仍避免满盘与显见
    if len(chosen) < target_count:
        remaining = [c for c in all_cells if c not in chosen]
        for c in remaining:
            i, j = c
            if row_counts[i] < n - 1 and col_counts[j] < n - 1:  # 保证至少各行列留 1 空
                chosen.append(c)
                row_counts[i] += 1
                col_counts[j] += 1
                if len(chosen) >= target_count:
                    break
    chosen = chosen[:target_count]
    return {c: _value_at(sol, c) for c in chosen}


# -------------------------------
# 高级线索生成工具（全部从解派生，避免矛盾）
# -------------------------------
def _generate_thermo_from_solution(sol: List[List[int]], n: int, rng: random.Random) -> Optional[Dict[str, Any]]:
    length = rng.randint(3, min(5, n + 1))
    path = _random_path_unique_orth(n, length, rng)
    if path is None:
        return None
    # 保持路径顺序，约束为严格递增
    return {'type': 'thermo_chain', 'cells': path}


def _generate_cage_sum_from_solution(sol: List[List[int]], n: int, rng: random.Random) -> Dict[str, Any]:
    k = rng.choice([2, 3, 4])
    cells = rng.sample(_all_cells_1_based(n), k)
    total = sum(_value_at(sol, c) for c in cells)
    return {'type': 'cage_sum', 'cells': cells, 'sum': total}


def _generate_region_all_diff(sol: List[List[int]], n: int, rng: random.Random) -> Dict[str, Any]:
    k = rng.choice([3, 4, 5])
    cells = rng.sample(_all_cells_1_based(n), k)
    return {'type': 'region_all_diff', 'cells': cells}


def _generate_line_segment_sum(sol: List[List[int]], n: int, rng: random.Random) -> Dict[str, Any]:
    length = rng.choice([2, 3, 4])
    if rng.choice([True, False]):
        i = rng.randint(1, n)
        start = rng.randint(1, n - length + 1)
        cells = [(i, start + t) for t in range(length)]
    else:
        j = rng.randint(1, n)
        start = rng.randint(1, n - length + 1)
        cells = [(start + t, j) for t in range(length)]
    total = sum(_value_at(sol, c) for c in cells)
    return {'type': 'line_segment_sum', 'cells': cells, 'sum': total}


def _hint_signature(h: Dict[str, Any]) -> Tuple:
    t = h['type']
    if t == 'pair_sum':
        a, b = h['a'], h['b']
        key = tuple(sorted([a, b]))
        return (t, key, h['sum'])
    if t == 'pair_diff_abs':
        a, b = h['a'], h['b']
        key = tuple(sorted([a, b]))
        return (t, key, h['diff'])
    if t == 'cell_parity':
        return (t, h['cell'], h['parity'])
    if t == 'cell_in_set':
        return (t, h['cell'], tuple(sorted(h['set'])))
    if t == 'value_position':
        if h['mode'] == 'row':
            return (t, 'row', h['i'], h['v'], h['j'])
        else:
            return (t, 'col', h['j'], h['v'], h['i'])
    if t == 'thermo_chain':
        return (t, tuple(h['cells']))
    if t == 'cage_sum':
        return (t, tuple(sorted(h['cells'])), h['sum'])
    if t == 'region_all_diff':
        return (t, tuple(sorted(h['cells'])))
    if t == 'line_segment_sum':
        return (t, tuple(h['cells']), h['sum'])
    if t in ('anti_knight', 'anti_king'):
        return (t,)
    return (t,)


# -------------------------------
# 额外线索生成（去重与配额控制）
# -------------------------------
def _generate_one_hint(sol: List[List[int]], n: int, hint_types: List[str],
                       used_signatures: Set[Tuple],
                       vp_quota: List[int],
                       rng: random.Random) -> Optional[Dict[str, Any]]:
    types = hint_types[:]
    rng.shuffle(types)
    cells = _all_cells_1_based(n)

    for t in types:
        if t == 'pair_sum':
            c1, c2 = rng.sample(cells, 2)
            s = _value_at(sol, c1) + _value_at(sol, c2)
            h = {'type': 'pair_sum', 'a': c1, 'b': c2, 'sum': s}
        elif t == 'pair_diff_abs':
            c1, c2 = rng.sample(cells, 2)
            d = abs(_value_at(sol, c1) - _value_at(sol, c2))
            if d == 0:
                continue
            h = {'type': 'pair_diff_abs', 'a': c1, 'b': c2, 'diff': d}
        elif t == 'cell_parity':
            c = rng.choice(cells)
            v = _value_at(sol, c)
            parity = 'even' if (v % 2 == 0) else 'odd'
            h = {'type': 'cell_parity', 'cell': c, 'parity': parity}
        elif t == 'cell_in_set':
            c = rng.choice(cells)
            all_vals = list(range(1, n + 1))
            v = _value_at(sol, c)
            k = rng.choice([2, 3])
            others = [x for x in all_vals if x != v]
            chosen = rng.sample(others, k - 1) + [v]
            rng.shuffle(chosen)
            h = {'type': 'cell_in_set', 'cell': c, 'set': chosen}
        elif t == 'value_position':
            if vp_quota[0] <= 0:
                continue
            if rng.choice([True, False]):
                i = rng.randint(1, n)
                v = rng.randint(1, n)
                jpos = sol[i - 1].index(v) + 1
                h = {'type': 'value_position', 'mode': 'row', 'i': i, 'v': v, 'j': jpos}
            else:
                j = rng.randint(1, n)
                v = rng.randint(1, n)
                col_vals = [sol[r][j - 1] for r in range(n)]
                ipos = col_vals.index(v) + 1
                h = {'type': 'value_position', 'mode': 'col', 'j': j, 'v': v, 'i': ipos}
        elif t == 'thermo_chain':
            h = _generate_thermo_from_solution(sol, n, rng)
            if h is None:
                continue
        elif t == 'cage_sum':
            h = _generate_cage_sum_from_solution(sol, n, rng)
        elif t == 'region_all_diff':
            h = _generate_region_all_diff(sol, n, rng)
        elif t == 'line_segment_sum':
            h = _generate_line_segment_sum(sol, n, rng)
        elif t in ('anti_knight','anti_king'):
            h = {'type': t}
        else:
            continue

        sig = _hint_signature(h)
        if sig in used_signatures:
            continue
        if h['type'] == 'value_position':
            vp_quota[0] -= 1
        used_signatures.add(sig)
        return h

    return None


# -------------------------------
# 将额外线索添加到 Z3 求解器
# -------------------------------
def _apply_hints(s: Solver, X: List[List[Any]], n: int, hints: List[Dict[str, Any]]):
    # 全局规则
    has_anti_knight = any(h.get('type') == 'anti_knight' for h in hints)
    has_anti_king = any(h.get('type') == 'anti_king' for h in hints)

    if has_anti_knight:
        knight_moves = [(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]
        for i in range(n):
            for j in range(n):
                for di, dj in knight_moves:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n and 0 <= nj < n:
                        s.add(X[i][j] != X[ni][nj])

    if has_anti_king:
        king_moves = [(1,1),(1,0),(1,-1),(0,1),(0,-1),(-1,1),(-1,0),(-1,-1)]
        for i in range(n):
            for j in range(n):
                for di, dj in king_moves:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n and 0 <= nj < n:
                        s.add(X[i][j] != X[ni][nj])

    # 局部约束
    for h in hints:
        t = h['type']
        if t == 'pair_sum':
            (i1, j1) = h['a']
            (i2, j2) = h['b']
            s.add(X[i1 - 1][j1 - 1] + X[i2 - 1][j2 - 1] == h['sum'])
        elif t == 'pair_diff_abs':
            (i1, j1) = h['a']
            (i2, j2) = h['b']
            d = h['diff']
            s.add(Or(X[i1 - 1][j1 - 1] - X[i2 - 1][j2 - 1] == d,
                     X[i2 - 1][j2 - 1] - X[i1 - 1][j1 - 1] == d))
        elif t == 'cell_parity':
            (i1, j1) = h['cell']
            evens = [k for k in range(1, n + 1) if k % 2 == 0]
            odds = [k for k in range(1, n + 1) if k % 2 == 1]
            s.add(Or(*[X[i1 - 1][j1 - 1] == k for k in (evens if h['parity'] == 'even' else odds)]))
        elif t == 'cell_in_set':
            (i1, j1) = h['cell']
            allowed = h['set']
            s.add(Or(*[X[i1 - 1][j1 - 1] == k for k in allowed]))
        elif t == 'value_position':
            v = h['v']
            if h['mode'] == 'row':
                i = h['i']
                j = h['j']
                s.add(X[i - 1][j - 1] == v)
            else:
                j = h['j']
                i = h['i']
                s.add(X[i - 1][j - 1] == v)
        elif t == 'thermo_chain':
            cells = h['cells']
            for a, b in zip(cells, cells[1:]):
                s.add(X[a[0]-1][a[1]-1] < X[b[0]-1][b[1]-1])
        elif t == 'cage_sum':
            cells = h['cells']
            total = h['sum']
            s.add(sum([X[c[0]-1][c[1]-1] for c in cells]) == total)
        elif t == 'region_all_diff':
            cells = h['cells']
            s.add(Distinct([X[c[0]-1][c[1]-1] for c in cells]))
        elif t == 'line_segment_sum':
            cells = h['cells']
            total = h['sum']
            s.add(sum([X[c[0]-1][c[1]-1] for c in cells]) == total)
        # 'anti_knight'/'anti_king' 已处理


# -------------------------------
# 唯一性检测（包含不等式、预填与额外线索），带超时
# -------------------------------
def _has_unique_solution(n: int,
                         givens: Dict[Tuple[int, int], int],
                         ineqs: List[Tuple[Tuple[int, int], Tuple[int, int], str]],
                         hints: List[Dict[str, Any]],
                         timeout_ms: int = 120000) -> bool:
    X = [[Int(f"x_{i+1}_{j+1}") for j in range(n)] for i in range(n)]

    # 第一次：找一个解
    s = Solver()
    s.set("timeout", timeout_ms)
    for i in range(n):
        for j in range(n):
            s.add(And(X[i][j] >= 1, X[i][j] <= n))
    for i in range(n):
        s.add(Distinct(X[i]))
    for j in range(n):
        s.add(Distinct([X[i][j] for i in range(n)]))
    for (a, b, op) in ineqs:
        ai, aj = a[0] - 1, a[1] - 1
        bi, bj = b[0] - 1, b[1] - 1
        s.add(X[ai][aj] > X[bi][bj] if op == 'gt' else X[ai][aj] < X[bi][bj])
    for (i1, j1), val in givens.items():
        s.add(X[i1 - 1][j1 - 1] == val)
    _apply_hints(s, X, n, hints)

    if s.check() != sat:
        return False
    m = s.model()
    first = [[m.evaluate(X[i][j]).as_long() for j in range(n)] for i in range(n)]

    # 第二次：寻找与 first 不同的解
    s2 = Solver()
    s2.set("timeout", timeout_ms)
    for i in range(n):
        for j in range(n):
            s2.add(And(X[i][j] >= 1, X[i][j] <= n))
    for i in range(n):
        s2.add(Distinct(X[i]))
    for j in range(n):
        s2.add(Distinct([X[i][j] for i in range(n)]))
    for (a, b, op) in ineqs:
        ai, aj = a[0] - 1, a[1] - 1
        bi, bj = b[0] - 1, b[1] - 1
        s2.add(X[ai][aj] > X[bi][bj] if op == 'gt' else X[ai][aj] < X[bi][bj])
    for (i1, j1), val in givens.items():
        s2.add(X[i1 - 1][j1 - 1] == val)
    _apply_hints(s2, X, n, hints)
    diff_or = Or(*[X[i][j] != first[i][j] for i in range(n) for j in range(n)])
    s2.add(diff_or)
    return s2.check() != sat


# -------------------------------
# 题目生成（含可变规则，优先添加逻辑线索，失败则重试）
# -------------------------------
def gen_futoshiki_instance(n: int,
                           given_cells_num: int,
                           ineq_num: int,
                           seed: Optional[int] = None,
                           hint_budget: int = 0,
                           hint_types: Optional[List[str]] = None,
                           max_attempts: int = 200,
                           timeout_ms: int = 120000) -> Dict[str, Any]:
    """
    逆向造题（增强版）：
    - 从随机拉丁方解出发，选取部分相邻不等式、部分预填与额外线索，使最终唯一。
    - 若到达上限仍不唯一，则整体重试，避免输出矛盾或显见题。
    - 控制线索数量与类型，保证题面可读与可推导。
    - 强制至少包含一条高价值线索，预填非显见（每行列最多 n-2）。
    """
    base_seed = seed if seed is not None else random.randint(1, 10**9)

    # 全量候选线索类型白名单
    full_allowed = [
        'pair_sum', 'pair_diff_abs', 'cell_parity', 'cell_in_set', 'value_position',
        'thermo_chain', 'cage_sum', 'region_all_diff', 'line_segment_sum', 'anti_knight', 'anti_king'
    ]
    high_value_set = {'thermo_chain', 'cage_sum', 'region_all_diff', 'line_segment_sum'}

    # 外层重试
    for regen_round in range(30):
        rng = random.Random(base_seed + regen_round)

        sol = _make_base_latin_square(n, rng)

        # 不等式初选（按照传入数量，后续可增量补充）
        all_pairs = _adjacent_pairs_1_based(n)
        rng.shuffle(all_pairs)
        ineq_num_clamped = max(n, min(ineq_num, len(all_pairs)))  # 至少 n 条
        selected_pairs = all_pairs[:ineq_num_clamped]
        ineqs = []
        for (a, b) in selected_pairs:
            op = _ineq_direction_from_solution(sol, a, b)
            ineqs.append((a, b, op))

        used_pairs = set(selected_pairs)
        unused_pairs = [p for p in all_pairs if p not in used_pairs]
        rng.shuffle(unused_pairs)

        # 预填初选（非显见，保证不是满盘；总量收紧到不超过 ceil(0.35*n*n) 与 n*n-1 的最小值）
        g_cap = min(n * n - 1, math.ceil(0.35 * n * n))
        given_cells_target = max(0, min(given_cells_num, g_cap))
        givens = _select_givens_nontrivial(n, sol, given_cells_target, rng)

        used_cells = set(givens.keys())
        unused_cells = [c for c in _all_cells_1_based(n) if c not in used_cells]
        rng.shuffle(unused_cells)

        # 线索类型与预算（至少 1）
        if hint_types is None:
            allowed = []
        else:
            allowed = [t for t in hint_types if t in full_allowed]
        if not allowed:
            # 保底加入高价值线索类型集
            allowed = ['thermo_chain', 'pair_diff_abs', 'cage_sum', 'region_all_diff']
        init_budget = max(1, min(hint_budget, n))  # 至少 1 条线索

        hints: List[Dict[str, Any]] = []
        used_sig: Set[Tuple] = set()

        # 全局规则一次性添加（若被选择）
        if 'anti_knight' in allowed:
            h = {'type': 'anti_knight'}
            used_sig.add(_hint_signature(h))
            hints.append(h)
        if 'anti_king' in allowed:
            h = {'type': 'anti_king'}
            used_sig.add(_hint_signature(h))
            hints.append(h)

        # 初始预算（优先高价值线索；剔除 value_position）
        vp_quota = [1]
        local_hint_candidates_init = [t for t in allowed if t not in ['anti_knight', 'anti_king', 'value_position']]
        # 强制至少一条高价值
        ensured_high = False
        for _ in range(init_budget):
            high_first = [t for t in local_hint_candidates_init if t in high_value_set]
            pick_pool = high_first if not ensured_high and high_first else local_hint_candidates_init
            h = _generate_one_hint(sol, n, pick_pool, used_sig, vp_quota, rng)
            if h is not None:
                hints.append(h)
                if h['type'] in high_value_set:
                    ensured_high = True

        # 增量唯一化：受上限约束，失败则重试
        attempts = 0
        max_more_hints = n
        # 预填兜底上限：不超过给定 + n，且不超过约 0.5*n*n
        max_givens = min(n * n - 1, min(len(givens) + n, int(0.5 * n * n)))
        # 控制不等式上限（在传入的基础上允许适度上浮）
        ineq_limit = min(2 * n * (n - 1), ineq_num_clamped + n)

        # 用于增量阶段的候选集合（不含全局规则）
        local_hint_candidates = [t for t in allowed if t not in ['anti_knight', 'anti_king']]
        # 避免过早使用 value_position
        local_hint_candidates_wo_vp = [t for t in local_hint_candidates if t != 'value_position']
        last_resort_types = ['value_position'] if 'value_position' in local_hint_candidates else []

        while attempts < max_attempts and not _has_unique_solution(n, givens, ineqs, hints, timeout_ms):
            attempts += 1
            # 先补不等式
            if unused_pairs and len(ineqs) < ineq_limit:
                p = unused_pairs.pop()
                op = _ineq_direction_from_solution(sol, p[0], p[1])
                ineqs.append((p[0], p[1], op))
                continue
            # 高价值线索优先
            high_value_types = [t for t in ['thermo_chain', 'cage_sum', 'line_segment_sum', 'region_all_diff'] if t in local_hint_candidates_wo_vp]
            non_global_hint_count = sum(1 for h in hints if h['type'] not in ['anti_knight', 'anti_king'])
            if non_global_hint_count < init_budget + max_more_hints and high_value_types:
                h = _generate_one_hint(sol, n, high_value_types, used_sig, vp_quota, rng)
                if h is not None:
                    hints.append(h)
                    continue
            # 其它线索（剔除 value_position）
            other_types = [t for t in local_hint_candidates_wo_vp if t not in high_value_set]
            non_global_hint_count = sum(1 for h in hints if h['type'] not in ['anti_knight', 'anti_king'])
            if non_global_hint_count < init_budget + max_more_hints and other_types:
                h = _generate_one_hint(sol, n, other_types, used_sig, vp_quota, rng)
                if h is not None:
                    hints.append(h)
                    continue
            # 最后兜底：必要时才加入 value_position（降低显见线索风险）
            if last_resort_types and vp_quota[0] > 0 and attempts > (max_attempts // 2):
                h = _generate_one_hint(sol, n, last_resort_types, used_sig, vp_quota, rng)
                if h is not None:
                    hints.append(h)
                    continue
            # 最后补预填（仍遵守非显见策略尽量选取）
            if unused_cells and len(givens) < max_givens:
                c = unused_cells.pop()
                givens[c] = _value_at(sol, c)
                continue
            # 达上限仍未唯一，跳出重试
            break

        # 若已唯一但没有高价值线索，则追加 1 条高价值线索（从解派生，不破坏唯一性）
        if _has_unique_solution(n, givens, ineqs, hints, timeout_ms):
            if not any(h['type'] in high_value_set for h in hints):
                extra_types = [t for t in ['thermo_chain', 'cage_sum', 'line_segment_sum', 'region_all_diff']]
                h_extra = _generate_one_hint(sol, n, extra_types, used_sig, vp_quota, rng)
                if h_extra is not None:
                    hints.append(h_extra)
            given_grid = [[None for _ in range(n)] for _ in range(n)]
            for (i, j), val in givens.items():
                given_grid[i - 1][j - 1] = val
            return {
                "n": n,
                "given_grid": given_grid,
                "ineqs": ineqs,
                "hints": hints,
                "final_grid": sol
            }
        # 否则进入下一轮 regen

    # 若多轮仍失败，抛出异常以便上层重试或报警
    raise RuntimeError("Failed to generate a unique Futoshiki instance within retry limits.")


# -------------------------------
# 文本与格式化（稳定化处理）
# -------------------------------
def format_grid(grid: List[List[Optional[int]]]) -> str:
    rows = []
    for r in grid:
        rows.append("[" + ", ".join([str(x) if x is not None else "X" for x in r]) + "]")
    return "[" + ", ".join(rows) + "]"


def format_ineqs(ineqs: List[Tuple[Tuple[int, int], Tuple[int, int], str]]) -> str:
    # 稳定排序，便于阅读
    def keyf(item):
        (a, b, op) = item
        return (a[0], a[1], b[0], b[1], op)
    parts = []
    for (a, b, op) in sorted(ineqs, key=keyf):
        sym = ">" if op == "gt" else "<"
        parts.append(f"({a[0]},{a[1]}) {sym} ({b[0]},{b[1]})")
    return "[" + ", ".join(parts) + "]"


def format_hints(hints: List[Dict[str, Any]]) -> str:
    # 稳定字符串表示，增强一致性
    tmp = []
    for h in hints:
        t = h['type']
        if t == 'pair_sum':
            a, b, s = h['a'], h['b'], h['sum']
            tmp.append(f"pair_sum:({a[0]},{a[1]})+({b[0]},{b[1]})={s}")
        elif t == 'pair_diff_abs':
            a, b, d = h['a'], h['b'], h['diff']
            tmp.append(f"pair_diff_abs:|({a[0]},{a[1]})-({b[0]},{b[1]})|={d}")
        elif t == 'cell_parity':
            c, p = h['cell'], h['parity']
            tmp.append(f"cell_parity:({c[0]},{c[1]}) is {p}")
        elif t == 'cell_in_set':
            c, S = h['cell'], sorted(h['set'])
            tmp.append(f"cell_in_set:({c[0]},{c[1]})∈[{', '.join(str(x) for x in S)}]")
        elif t == 'value_position':
            v = h['v']
            if h['mode'] == 'row':
                i, j = h['i'], h['j']
                tmp.append(f"value_position:R{i} has {v} at C{j}")
            else:
                j, i = h['j'], h['i']
                tmp.append(f"value_position:C{j} has {v} at R{i}")
        elif t == 'thermo_chain':
            cells = h['cells']
            tmp.append("thermo_chain:" + "->".join([f"({c[0]},{c[1]})" for c in cells]))
        elif t == 'cage_sum':
            cells = h['cells']
            total = h['sum']
            tmp.append("cage_sum[" + ", ".join([f"({c[0]},{c[1]})" for c in cells]) + f"]={total}")
        elif t == 'region_all_diff':
            cells = h['cells']
            tmp.append("region_all_diff[" + ", ".join([f"({c[0]},{c[1]})" for c in cells]) + "]")
        elif t == 'line_segment_sum':
            cells = h['cells']
            total = h['sum']
            tmp.append("line_segment_sum[" + ", ".join([f"({c[0]},{c[1]})" for c in cells]) + f"]={total}")
        elif t == 'anti_knight':
            tmp.append("anti_knight")
        elif t == 'anti_king':
            tmp.append("anti_king")
    parts = sorted(tmp)
    return "[" + ", ".join(parts) + "]"


def sample_sublist(base: List[str], seed: Optional[int] = None) -> List[str]:
    """随机挑选子集；允许空集以表示无额外线索/全局规则；受 seed 控制以保证复现。"""
    if not base:
        return []
    rng = random.Random(seed) if seed is not None else random
    k = rng.randint(0, len(base))
    return rng.sample(base, k)


def sample_choice(options: List[str], seed: Optional[int] = None) -> str:
    """从字符串列表中抽一个值；受 seed 控制以保证复现。"""
    if not options:
        return ""
    rng = random.Random(seed) if seed is not None else random
    return rng.choice(options)


def compose_rule_text(n: int, hints: List[Dict[str, Any]]) -> str:
    """规则句式合成：包含坐标说明、X 的含义与题面实际出现的线索类型简释；不含双引号与单引号字符。"""
    base_alts = [
        f"每行与每列都需填写 1..{n} 且不重复",
        f"行列均为 1..{n} 的排列且不重复",
        f"每一行每一列包含 1..{n} 且不得重复"
    ]
    ineq_alts = [
        "相邻格之间给出部分大小不等约束",
        "相邻单元存在部分大于或小于的比较提示",
        "部分相邻位置带有大于或小于的提示"
    ]
    hint_map = {
        'pair_sum': "两格和等式(两格之和等于给定值)",
        'pair_diff_abs': "两格差的绝对值(两格差的绝对值等于给定值)",
        'cell_parity': "单元格奇偶性(某格为奇数或偶数)",
        'cell_in_set': "单元格取值范围(某格值属于给定候选集)",
        'value_position': "数值位置信息(某行或某列中某数的确切位置)",
        'thermo_chain': "温度计链(沿链值严格递增)",
        'cage_sum': "小笼求和(若干格之和等于目标)",
        'region_all_diff': "小域全异(给定若干格两两不同)",
        'line_segment_sum': "行或列片段和(连续片段的总和给定)",
        'anti_knight': "反骑士(骑士步相距的两格不得相等)",
        'anti_king': "反国王(王步相邻的两格不得相等)"
    }
    # 汇总题面实际出现的线索类型
    used_types = []
    for h in hints:
        t = h.get('type')
        if t in hint_map and t not in used_types:
            used_types.append(t)
    extra = [hint_map[h] for h in used_types]
    if extra:
        extra_text = "；术语说明：" + "、".join(extra)
    else:
        extra_text = "；术语说明：本题无额外线索或仅有相邻不等式提示"
    coord_text = "；坐标与 R/C 编号均从 1 开始计数，坐标写作 (行,列)"
    x_meaning = "；题面矩阵中的 X 表示未给定的空格"
    # 采用一个固定句式组合，避免产生双引号或单引号
    return base_alts[0] + "；" + ineq_alts[0] + coord_text + x_meaning + extra_text