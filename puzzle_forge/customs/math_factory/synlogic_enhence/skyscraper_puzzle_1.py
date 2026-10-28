# skyscraper_puzzle_1.py
# -----------------------------------------------------------------------------
# 高阶逆向生成与唯一解验证工具集（无需 Z3）：
# - generate_instance(n, base_max, time_limit_sec): 生成完整实例并确保唯一解（<= 指定秒数）
#   内部使用：
#   * solve_latin(n): 拉丁方生成（循环拉丁方 + 随机数字/行/列置换）
#   * gen_base(n, min_b, max_b): 地基生成
#   * compute_clues(base, grid, metric_type, view_rule): 广义线索计算
#   * unique_solver(...): 强剪枝回溯计数解（数到2停止），支持多元复合约束与前缀边界
#   * 自适配增强：逐步加约束或降低线索掩码，必要时全显+全约束回退
# - format_clues: 线索文本渲染（未知为 '?'）
# -----------------------------------------------------------------------------

import random
import time
from typing import List, Tuple, Dict, Any, Optional


def _permute_list(l: List[int]) -> List[int]:
    l2 = l[:]
    random.shuffle(l2)
    return l2


def solve_latin(n: int) -> List[List[int]]:
    """随机生成 n×n 拉丁方：循环拉丁方 + 随机数字映射 + 行/列置换。"""
    L = [[(i + j) % n + 1 for j in range(n)] for i in range(n)]
    digits = list(range(1, n + 1))
    shuffled = digits[:]
    random.shuffle(shuffled)
    map_digit = {d: shuffled[d - 1] for d in digits}
    L = [[map_digit[v] for v in row] for row in L]
    row_perm = _permute_list(list(range(n)))
    col_perm = _permute_list(list(range(n)))
    L = [[L[row_perm[i]][col_perm[j]] for j in range(n)] for i in range(n)]
    # 校验行列全异
    for r in range(n):
        assert len(set(L[r])) == n
    for c in range(n):
        assert len(set(L[r][c] for r in range(n))) == n
    return L


def gen_base(n: int, min_b: int, max_b: int) -> List[List[int]]:
    """生成 n×n 地基矩阵，元素在 [min_b, max_b]。"""
    if max_b < min_b:
        max_b = min_b
    return [[random.randint(min_b, max_b) for _ in range(n)] for _ in range(n)]


def _visible_count(seq: List[int], rule: str) -> int:
    """可见度计数：strict（>）或 ge（>=）。"""
    cnt = 0
    mx = float('-inf')
    if rule == 'strict':
        for v in seq:
            if v > mx:
                cnt += 1
                mx = v
    elif rule == 'ge':
        for v in seq:
            if v >= mx:
                cnt += 1
                mx = v
    else:
        raise ValueError("Unknown view rule.")
    return cnt


def compute_clues(base: List[List[int]], grid: List[List[int]],
                  metric_type: str, view_rule: str) -> Dict[str, List[int]]:
    """广义线索计算：metric_type ∈ {'total','height'}, view_rule ∈ {'strict','ge'}。"""
    n = len(base)
    assert n == len(grid)
    def val(r: int, c: int) -> int:
        return base[r][c] + grid[r][c] if metric_type == 'total' else grid[r][c]
    left, right, top, bottom = [], [], [], []
    for r in range(n):
        seq = [val(r, c) for c in range(n)]
        left.append(_visible_count(seq, view_rule))
        right.append(_visible_count(list(reversed(seq)), view_rule))
    for c in range(n):
        seq = [val(r, c) for r in range(n)]
        top.append(_visible_count(seq, view_rule))
        bottom.append(_visible_count(list(reversed(seq)), view_rule))
    return {'left': left, 'right': right, 'top': top, 'bottom': bottom}


def format_clues(top: List[Any], bottom: List[Any], left: List[Any], right: List[Any]) -> str:
    """线索文本渲染：未知为 '?'。"""
    def fmt(arr: List[Any]) -> List[str]:
        return [('?' if x is None else str(int(x))) for x in arr]
    ts = ', '.join(fmt(top))
    bs = ', '.join(fmt(bottom))
    ls = ', '.join(fmt(left))
    rs = ', '.join(fmt(right))
    return f"top=[{ts}] bottom=[{bs}] left=[{ls}] right=[{rs}]"


# ------------------------- 唯一解验证求解器 -------------------------

class SolverCtx:
    """封装约束上下文，便于在回溯中高效判断与剪枝。"""
    def __init__(self, n: int, base: List[List[int]], metric_type: str, view_rule: str,
                 fixed_cells: List[Tuple[int, int, int]],
                 shown_clues: Dict[str, List[Optional[int]]],
                 row_weights: List[int], col_weights: List[int],
                 row_weights2: List[int], col_weights2: List[int],
                 row_sums: List[Tuple[int, int]], col_sums: List[Tuple[int, int]],
                 row_sums2: List[Tuple[int, int]], col_sums2: List[Tuple[int, int]],
                 odd_rows: List[Tuple[int, int]],
                 peak_rows: List[Tuple[int, int]], peak_cols: List[Tuple[int, int]],
                 diag_weights: List[int], anti_diag_weights: List[int],
                 diag_sum: int, anti_diag_sum: int):
        self.n = n
        self.base = base
        self.metric_type = metric_type
        self.view_rule = view_rule
        self.fixed_map = {(r, c): v for (r, c, v) in fixed_cells}
        self.top = shown_clues['top']
        self.bottom = shown_clues['bottom']
        self.left = shown_clues['left']
        self.right = shown_clues['right']
        self.row_weights = row_weights
        self.col_weights = col_weights
        self.row_weights2 = row_weights2
        self.col_weights2 = col_weights2
        self.row_sums_map = {r: s for (r, s) in row_sums}
        self.col_sums_map = {c: s for (c, s) in col_sums}
        self.row_sums2_map = {r: s for (r, s) in row_sums2}
        self.col_sums2_map = {c: s for (c, s) in col_sums2}
        self.odd_rows_map = {r: k for (r, k) in odd_rows}
        self.peak_rows_map = {r: p for (r, p) in peak_rows}  # 1-based
        self.peak_cols_map = {c: p for (c, p) in peak_cols}  # 1-based
        self.diag_weights = diag_weights
        self.anti_diag_weights = anti_diag_weights
        self.diag_sum = diag_sum
        self.anti_diag_sum = anti_diag_sum

    def val(self, r: int, c: int, h: int) -> int:
        return self.base[r][c] + h if self.metric_type == 'total' else h


def _peak_pos(vals: List[int]) -> int:
    """返回最大值首次出现位置（1-based）。"""
    m = max(vals)
    for i, v in enumerate(vals):
        if v == m:
            return i + 1
    return 1


def precompute_row_candidates(ctx: SolverCtx) -> List[List[List[int]]]:
    """为每行预筛候选排列，满足固定格、左右线索、行加权和、备用加权和、奇偶计数、行峰位。"""
    n = ctx.n
    all_perms = [list(p) for p in __import__('itertools').permutations(range(1, n + 1))]
    row_candidates: List[List[List[int]]] = [[] for _ in range(n)]
    for r in range(n):
        candidates_r = []
        for perm in all_perms:
            ok = True
            # 固定格
            for c in range(n):
                vfix = ctx.fixed_map.get((r, c))
                if vfix is not None and perm[c] != vfix:
                    ok = False
                    break
            if not ok:
                continue
            # 左右线索（如已知）
            lv = ctx.left[r]
            rv = ctx.right[r]
            seq_vals = [ctx.val(r, c, perm[c]) for c in range(n)]
            if lv is not None and _visible_count(seq_vals, ctx.view_rule) != lv:
                continue
            if rv is not None and _visible_count(list(reversed(seq_vals)), ctx.view_rule) != rv:
                continue
            # 行加权和
            if r in ctx.row_sums_map:
                s = sum(ctx.row_weights[c] * perm[c] for c in range(n))
                if s != ctx.row_sums_map[r]:
                    continue
            # 行备用加权和
            if r in ctx.row_sums2_map:
                s2 = sum(ctx.row_weights2[c] * perm[c] for c in range(n))
                if s2 != ctx.row_sums2_map[r]:
                    continue
            # 奇偶计数
            if r in ctx.odd_rows_map:
                k = sum(1 for c in range(n) if perm[c] % 2 == 1)
                if k != ctx.odd_rows_map[r]:
                    continue
            # 行峰位约束
            if r in ctx.peak_rows_map:
                pos = _peak_pos(seq_vals)
                if pos != ctx.peak_rows_map[r]:
                    continue
            candidates_r.append(perm)
        if not candidates_r:
            return []
        row_candidates[r] = candidates_r
    return row_candidates


def unique_solver(n: int, ctx: SolverCtx, time_limit_sec: float) -> Tuple[int, Optional[List[List[int]]]]:
    """
    强剪枝回溯计数解，最多到 2；返回 (solution_count, first_solution)。
    剪枝要点：
    - 列唯一性；
    - 列加权和/备用加权和的前缀上下界（基于剩余可用数字与权重）；
    - 列上视线 top 的前缀可见度不超；
    - 对角线最终检查；
    - MRV：按照行候选数排序。
    """
    start = time.time()
    row_candidates = precompute_row_candidates(ctx)
    if not row_candidates:
        return 0, None

    grid = [[0] * n for _ in range(n)]
    col_used = [set() for _ in range(n)]

    sol_count = 0
    first_sol = None

    def time_ok():
        return (time.time() - start) <= time_limit_sec

    # MRV 排序
    row_order = list(range(n))
    row_order.sort(key=lambda r: len(row_candidates[r]))
    idx_to_row = {i: row_order[i] for i in range(n)}

    def col_bounds_ok(ridx: int) -> bool:
        """列加权和前缀上下界剪枝（两套权重）。"""
        row_real = idx_to_row[ridx]
        # 计算剩余行集合（尚未填充的真实行号）
        remaining_rows = [idx_to_row[i] for i in range(ridx + 1, n)]
        for c in range(n):
            remaining_nums = [x for x in range(1, n + 1) if x not in col_used[c]]
            # 上下界（按当前列权重与备用权重分别估计）
            if c in ctx.col_sums_map or c in ctx.col_sums2_map:
                # 已填部分的贡献
                cur_sum = sum(ctx.col_weights[r] * grid[r][c] for r in range(n) if grid[r][c] != 0)
                cur_sum2 = sum(ctx.col_weights2[r] * grid[r][c] for r in range(n) if grid[r][c] != 0)
                # 剩余权重
                rem_w = [ctx.col_weights[r] for r in remaining_rows]
                rem_w2 = [ctx.col_weights2[r] for r in remaining_rows]
                # 排序以取极端界（贪心逼近）
                remaining_nums_sorted = sorted(remaining_nums)
                remaining_nums_sorted_desc = sorted(remaining_nums, reverse=True)
                rem_w_sorted = sorted(rem_w)
                rem_w_sorted_desc = sorted(rem_w, reverse=True)
                rem_w2_sorted = sorted(rem_w2)
                rem_w2_sorted_desc = sorted(rem_w2, reverse=True)
                # 下界：最小数字配最小权重；上界：最大数字配最大权重
                lb = cur_sum + sum(a * b for a, b in zip(remaining_nums_sorted, rem_w_sorted))
                ub = cur_sum + sum(a * b for a, b in zip(remaining_nums_sorted_desc, rem_w_sorted_desc))
                lb2 = cur_sum2 + sum(a * b for a, b in zip(remaining_nums_sorted, rem_w2_sorted))
                ub2 = cur_sum2 + sum(a * b for a, b in zip(remaining_nums_sorted_desc, rem_w2_sorted_desc))
                if c in ctx.col_sums_map:
                    target = ctx.col_sums_map[c]
                    if target < lb or target > ub:
                        return False
                if c in ctx.col_sums2_map:
                    target2 = ctx.col_sums2_map[c]
                    if target2 < lb2 or target2 > ub2:
                        return False
        return True

    def feasible_top_prefix(ridx: int) -> bool:
        """列上视线 top 的前缀可见度不超过已知值。"""
        row_real = idx_to_row[ridx]
        for c in range(n):
            if ctx.top[c] is None:
                continue
            # 计算前缀序列
            seq = []
            for r in range(row_real + 1):
                h = grid[r][c]
                if h == 0:
                    seq.append(float('-inf'))  # 未填视为不可见
                else:
                    seq.append(ctx.val(r, c, h))
            if _visible_count(seq, ctx.view_rule) > ctx.top[c]:
                return False
        return True

    def place_row(ridx: int):
        nonlocal sol_count, first_sol
        if not time_ok() or sol_count >= 2:
            return
        if ridx == n:
            # 终检：列唯一性、列上下线索、列加权和两套、列峰位、对角线约束
            # 列唯一性
            for c in range(n):
                col_vals = [grid[r][c] for r in range(n)]
                if len(set(col_vals)) != n:
                    return
            # 列上下线索
            for c in range(n):
                seq = [ctx.val(r, c, grid[r][c]) for r in range(n)]
                if ctx.top[c] is not None and _visible_count(seq, ctx.view_rule) != ctx.top[c]:
                    return
                if ctx.bottom[c] is not None and _visible_count(list(reversed(seq)), ctx.view_rule) != ctx.bottom[c]:
                    return
            # 列加权和两套
            for c in range(n):
                if c in ctx.col_sums_map:
                    s = sum(ctx.col_weights[r] * grid[r][c] for r in range(n))
                    if s != ctx.col_sums_map[c]:
                        return
                if c in ctx.col_sums2_map:
                    s2 = sum(ctx.col_weights2[r] * grid[r][c] for r in range(n))
                    if s2 != ctx.col_sums2_map[c]:
                        return
            # 列峰位
            for c in range(n):
                if c in ctx.peak_cols_map:
                    seq = [ctx.val(r, c, grid[r][c]) for r in range(n)]
                    if _peak_pos(seq) != ctx.peak_cols_map[c]:
                        return
            # 对角线约束
            ds = sum(ctx.diag_weights[i] * grid[i][i] for i in range(n))
            ads = sum(ctx.anti_diag_weights[i] * grid[i][n - 1 - i] for i in range(n))
            if ds != ctx.diag_sum or ads != ctx.anti_diag_sum:
                return
            # 计解
            sol_count += 1
            if first_sol is None:
                first_sol = [row[:] for row in grid]
            return

        row_real = idx_to_row[ridx]
        for perm in row_candidates[row_real]:
            # 列唯一性剪枝
            ok = True
            for c in range(n):
                if perm[c] in col_used[c]:
                    ok = False
                    break
            if not ok:
                continue
            # 放置
            for c in range(n):
                grid[row_real][c] = perm[c]
                col_used[c].add(perm[c])
            # 前缀剪枝
            if feasible_top_prefix(ridx) and col_bounds_ok(ridx):
                place_row(ridx + 1)
            # 回溯
            for c in range(n):
                col_used[c].remove(perm[c])
                grid[row_real][c] = 0
            if sol_count >= 2 or not time_ok():
                return

    place_row(0)
    return sol_count, first_sol


# ------------------------- 自适配实例生成 -------------------------

def generate_instance(n: int, base_max: int, time_limit_sec: float) -> Dict[str, Any]:
    """
    生成完整实例并确保唯一解：
    - 随机 grid（拉丁方）、base、metric_type、view_rule；
    - 计算完整线索 clues，并随机掩码部分线索；
    - 随机生成多元复合约束（两套行/列权重与加权和、奇偶计数、峰位、主/副对角线约束）；
    - 调用 unique_solver 验证；若无解或非唯一则调整直至成功或达到时间限制，随后强约束回退确保产出。
    """
    start = time.time()
    rnd = random.Random()

    grid = solve_latin(n)
    base = gen_base(n, 0, base_max)
    metric_type = rnd.choice(['total', 'height'])
    view_rule = rnd.choice(['strict', 'ge'])
    clues_full = compute_clues(base, grid, metric_type, view_rule)

    # 固定格数量（适中）
    fixed_num = rnd.randint(0, n)
    all_positions = [(r, c) for r in range(n) for c in range(n)]
    fixed_positions = rnd.sample(all_positions, fixed_num)
    fixed_cells = [(r, c, grid[r][c]) for (r, c) in fixed_positions]

    # 初始线索掩码比例（较保守，避免过度遮掩）
    mask_ratio = rnd.randint(10, 40)

    def mask_clues_local(clues: Dict[str, List[int]], ratio: int) -> Dict[str, List[Optional[int]]]:
        masked = {}
        for k in ['top', 'bottom', 'left', 'right']:
            arr = clues[k][:]
            m = round(n * max(0, min(100, ratio)) / 100.0)
            idxs = list(range(n))
            rnd.shuffle(idxs)
            to_mask = set(idxs[:m])
            masked[k] = [None if i in to_mask else arr[i] for i in range(n)]
        return masked

    # 两套权重
    row_weights = [rnd.randint(1, 3) for _ in range(n)]
    col_weights = [rnd.randint(1, 3) for _ in range(n)]
    row_weights2 = [rnd.randint(1, 3) for _ in range(n)]
    col_weights2 = [rnd.randint(1, 3) for _ in range(n)]

    # 初始约束集合（覆盖度较高但非全部）
    rows_for_sum = rnd.sample(list(range(n)), rnd.randint(max(1, n // 2), n))
    cols_for_sum = rnd.sample(list(range(n)), rnd.randint(max(1, n // 2), n))
    rows_for_sum2 = rnd.sample(list(range(n)), rnd.randint(max(1, n // 2), n))
    cols_for_sum2 = rnd.sample(list(range(n)), rnd.randint(max(1, n // 2), n))

    row_sums = [(r, sum(row_weights[c] * grid[r][c] for c in range(n))) for r in rows_for_sum]
    col_sums = [(c, sum(col_weights[r] * grid[r][c] for r in range(n))) for c in cols_for_sum]
    row_sums2 = [(r, sum(row_weights2[c] * grid[r][c] for c in range(n))) for r in rows_for_sum2]
    col_sums2 = [(c, sum(col_weights2[r] * grid[r][c] for r in range(n))) for c in cols_for_sum2]

    # 奇偶与峰位
    odd_rows_pick = rnd.sample(list(range(n)), rnd.randint(0, n // 2))
    odd_rows = [(r, sum(1 for c in range(n) if grid[r][c] % 2 == 1)) for r in odd_rows_pick]

    def row_metric_vals(r: int) -> List[int]:
        return [base[r][c] + grid[r][c] if metric_type == 'total' else grid[r][c] for c in range(n)]
    def col_metric_vals(c: int) -> List[int]:
        return [base[r][c] + grid[r][c] if metric_type == 'total' else grid[r][c] for r in range(n)]

    peak_rows_pick = rnd.sample(list(range(n)), rnd.randint(0, n // 2))
    peak_cols_pick = rnd.sample(list(range(n)), rnd.randint(0, n // 2))
    peak_rows = [(r, _peak_pos(row_metric_vals(r))) for r in peak_rows_pick]
    peak_cols = [(c, _peak_pos(col_metric_vals(c))) for c in peak_cols_pick]

    # 对角线约束（权重与和）
    diag_weights = [rnd.randint(1, 3) for _ in range(n)]
    anti_diag_weights = [rnd.randint(1, 3) for _ in range(n)]
    diag_sum = sum(diag_weights[i] * grid[i][i] for i in range(n))
    anti_diag_sum = sum(anti_diag_weights[i] * grid[i][n - 1 - i] for i in range(n))

    shown_clues = mask_clues_local(clues_full, mask_ratio)
    adjust_step = 0
    first_solution: Optional[List[List[int]]] = None

    while True:
        elapsed = time.time() - start
        if elapsed > time_limit_sec:
            # 超时回退：全显线索+全约束
            shown_clues = clues_full
            row_sums = [(r, sum(row_weights[c] * grid[r][c] for c in range(n))) for r in range(n)]
            col_sums = [(c, sum(col_weights[r] * grid[r][c] for r in range(n))) for c in range(n)]
            row_sums2 = [(r, sum(row_weights2[c] * grid[r][c] for c in range(n))) for r in range(n)]
            col_sums2 = [(c, sum(col_weights2[r] * grid[r][c] for r in range(n))) for c in range(n)]
            odd_rows = [(r, sum(1 for c in range(n) if grid[r][c] % 2 == 1)) for r in range(n)]
            peak_rows = [(r, _peak_pos(row_metric_vals(r))) for r in range(n)]
            peak_cols = [(c, _peak_pos(col_metric_vals(c))) for c in range(n)]
            break

        ctx = SolverCtx(n, base, metric_type, view_rule,
                        fixed_cells, shown_clues,
                        row_weights, col_weights,
                        row_weights2, col_weights2,
                        row_sums, col_sums,
                        row_sums2, col_sums2,
                        odd_rows, peak_rows, peak_cols,
                        diag_weights, anti_diag_weights, diag_sum, anti_diag_sum)
        remaining_time = max(0.5, time_limit_sec - elapsed)
        count, sol = unique_solver(n, ctx, remaining_time)
        if count == 1:
            first_solution = sol
            break
        elif count == 0:
            # 无解：降低掩码或增加约束（优先 reveal 更多线索，再补充约束）
            mask_ratio = max(0, mask_ratio - rnd.randint(5, 12))
            shown_clues = mask_clues_local(clues_full, mask_ratio)
            # 增强约束：补齐未覆盖的行/列加权和或峰位
            if adjust_step % 2 == 0 and len(row_sums) < n:
                add_r = rnd.choice([x for x in range(n) if x not in [r for r, _ in row_sums]])
                row_sums.append((add_r, sum(row_weights[c] * grid[add_r][c] for c in range(n))))
            elif len(col_sums) < n:
                add_c = rnd.choice([x for x in range(n) if x not in [c for c, _ in col_sums]])
                col_sums.append((add_c, sum(col_weights[r] * grid[r][add_c] for r in range(n))))
            if len(row_sums2) < n:
                add_r2 = rnd.choice([x for x in range(n) if x not in [r for r, _ in row_sums2]])
                row_sums2.append((add_r2, sum(row_weights2[c] * grid[add_r2][c] for c in range(n))))
            if len(col_sums2) < n:
                add_c2 = rnd.choice([x for x in range(n) if x not in [c for c, _ in col_sums2]])
                col_sums2.append((add_c2, sum(col_weights2[r] * grid[r][add_c2] for r in range(n))))
            # 偶尔增加峰位
            if rnd.random() < 0.5 and len(peak_rows) < n:
                add_rp = rnd.choice([x for x in range(n) if x not in [r for r, _ in peak_rows]])
                peak_rows.append((add_rp, _peak_pos(row_metric_vals(add_rp))))
            adjust_step += 1
        else:  # count >= 2 非唯一
            # 非唯一：增加约束或降低掩码
            if len(peak_cols) < n:
                add_cp = rnd.choice([x for x in range(n) if x not in [c for c, _ in peak_cols]])
                peak_cols.append((add_cp, _peak_pos(col_metric_vals(add_cp))))
            else:
                mask_ratio = max(0, mask_ratio - rnd.randint(5, 12))
                shown_clues = mask_clues_local(clues_full, mask_ratio)
            adjust_step += 1

    if first_solution is None:
        first_solution = grid

    # 输出实例
    return {
        'base': base,
        'grid': first_solution,
        'metric_type': metric_type,
        'view_rule': view_rule,
        'fixed_cells': fixed_cells,
        'shown_clues': mask_clues_local(clues_full, mask_ratio) if (time.time() - start) <= time_limit_sec else clues_full,
        'row_weights': row_weights,
        'col_weights': col_weights,
        'row_weights2': row_weights2,
        'col_weights2': col_weights2,
        'row_sums': row_sums,
        'col_sums': col_sums,
        'row_sums2': row_sums2,
        'col_sums2': col_sums2,
        'odd_rows': odd_rows,
        'peak_rows': peak_rows,
        'peak_cols': peak_cols,
        'diag_weights': diag_weights,
        'anti_diag_weights': anti_diag_weights,
        'diag_sum': diag_sum,
        'anti_diag_sum': anti_diag_sum,
        'unique_flag': True
    }